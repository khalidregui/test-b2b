"""Unit tests for the GlobalConcurrencyLimiter.

These tests focus on realistic, production-grade scenarios that are prone to
break under load or in edge cases (e.g., queued tasks, start-time spacing,
exception safety, and live statistics). Simpler happy-path checks are avoided
in favor of conditions that would meaningfully signal regressions.
"""

import asyncio
import time
from typing import List

import pytest

from backend.services.rate_limiters.global_concurrency_limiter import (
    ConcurrencyLimitConfig,
    GlobalConcurrencyLimiter,
    _load_limiter_config,
)


async def _run_job(
    limiter: GlobalConcurrencyLimiter,
    job_name: str,
    work_duration: float,
    start_times: List[float],
    index: int,
    counter: dict,
    lock: asyncio.Lock,
):
    """Helper to execute a job under the limiter and record timings.

    Args:
      limiter: The concurrency limiter instance.
      job_name: Identifier of the job for logging and tracking.
      work_duration: Simulated work duration inside the critical section.
      start_times: Shared list to record the entry time into the job body.
      index: Index where to store the entry time for the current job.
      counter: Shared dict holding keys 'current' and 'max_seen' for concurrency.
      lock: Lock to protect counter updates for deterministic assertions.
    """
    # Acquire the limiter's permit; this is where queuing and min-delay logic applies.
    async with limiter.acquire(job_name):
        # Record the start time of the job's body (post-delay if configured).
        start_times[index] = time.perf_counter()

        # Update concurrency counters safely to compute "max concurrent seen".
        async with lock:
            counter["current"] += 1
            counter["max_seen"] = max(counter["max_seen"], counter["current"])

        # Simulate actual work while holding the permit.
        await asyncio.sleep(work_duration)

        # Decrement current concurrency once work completes.
        async with lock:
            counter["current"] -= 1


@pytest.mark.asyncio
async def test_limits_max_concurrency_and_queueing():
    """Validate that jobs beyond the limit are queued, not run concurrently.

    Why this matters:
      In production, if the limiter leaks permits or doesn't queue properly,
      CPU/memory spikes can overload the VM. Here we verify that with 5 jobs,
      no more than 2 run at the same time and total runtime reflects batching.
    """
    # Configure for at most 2 concurrent jobs and no inter-start delay.
    limiter = GlobalConcurrencyLimiter(
        ConcurrencyLimitConfig(max_concurrent_jobs=2, min_delay_between_jobs=0.0)
    )

    # Shared state to track concurrency and start times for each task.
    n_jobs = 5
    work_duration = 0.2
    start_times = [0.0] * n_jobs
    counter = {"current": 0, "max_seen": 0}
    lock = asyncio.Lock()

    # Launch all jobs together to pressure the concurrency limit.
    t0 = time.perf_counter()
    tasks = [
        asyncio.create_task(
            _run_job(limiter, f"job-{i}", work_duration, start_times, i, counter, lock)
        )
        for i in range(n_jobs)
    ]

    # Wait for all jobs to complete.
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0

    # Assert that at most 2 jobs ever ran concurrently.
    assert counter["max_seen"] <= 2

    # With 5 jobs and 2-wide concurrency, runtime should be ~3 batches of 0.2s ≈ 0.6s.
    # If permits leak and more than 2 run, this duration would drop substantially.
    expected_min = work_duration * ((n_jobs + 2 - 1) // 2)  # ceil(n/2) * 0.2
    assert elapsed >= expected_min * 0.9  # allow light scheduler jitter


@pytest.mark.asyncio
async def test_min_delay_between_jobs_enforced_serial_start():
    """Ensure min_delay_between_jobs spaces out job starts even with free slots.

    Why this matters:
      A thundering herd of heavy jobs can still saturate resources even if
      concurrency is respected. The optional min-delay feature reduces such
      spikes by spacing starts; this test verifies those gaps actually occur.
    """
    # Allow ample concurrency but enforce start spacing.
    delay = 0.1
    limiter = GlobalConcurrencyLimiter(
        ConcurrencyLimitConfig(max_concurrent_jobs=3, min_delay_between_jobs=delay)
    )

    # Three lightweight jobs; measured entry times should be spaced by ~delay.
    n_jobs = 3
    start_times = [0.0] * n_jobs
    counter = {"current": 0, "max_seen": 0}
    lock = asyncio.Lock()

    tasks = [
        asyncio.create_task(_run_job(limiter, f"job-{i}", 0.01, start_times, i, counter, lock))
        for i in range(n_jobs)
    ]
    await asyncio.gather(*tasks)

    # Sort entry times and check that consecutive starts are spaced by the delay.
    sorted_times = sorted(start_times)
    gaps = [b - a for a, b in zip(sorted_times, sorted_times[1:])]

    # Use a small epsilon to account for event loop jitter.
    assert all(gap >= delay * 0.9 for gap in gaps)


@pytest.mark.asyncio
async def test_exception_does_not_leak_permits():
    """Verify that an exception inside the context releases the semaphore.

    Why this matters:
      If an error path fails to release the permit, subsequent jobs deadlock,
      causing production outages. We simulate a failure then ensure the next
      job proceeds normally and stats reflect full availability post-run.
    """
    limiter = GlobalConcurrencyLimiter(
        ConcurrencyLimitConfig(max_concurrent_jobs=1, min_delay_between_jobs=0.0)
    )

    async def failing_job():
        async with limiter.acquire("failing"):
            # Raise inside the critical section to test release-on-exit logic.
            raise RuntimeError("boom")

    async def succeeding_job():
        async with limiter.acquire("succeeding"):
            await asyncio.sleep(0.05)
            return "ok"

    # Launch both jobs; the second should wait for the first to release.
    t0 = time.perf_counter()
    task1 = asyncio.create_task(failing_job())
    task2 = asyncio.create_task(succeeding_job())

    # Swallow the expected error from the first job.
    with pytest.raises(RuntimeError):
        await task1

    # The second job must complete quickly, demonstrating no deadlock.
    result = await asyncio.wait_for(task2, timeout=1.0)
    elapsed = time.perf_counter() - t0

    assert result == "ok"
    assert elapsed < 0.5  # if permit leaked, this would likely time out

    # After both tasks, all slots should be available and no active jobs remain.
    stats = limiter.get_stats()
    assert stats["available_slots"] == 1
    assert stats["current_active_jobs"] == 0


@pytest.mark.asyncio
async def test_stats_reflect_live_activity_and_reset():
    """Check that get_stats reflects live activity and reset clears registry.

    Why this matters:
      Operational dashboards and autoscaling logic rely on accurate stats.
      We verify counts while jobs are in-flight and after a state reset.
    """
    limiter = GlobalConcurrencyLimiter(
        ConcurrencyLimitConfig(max_concurrent_jobs=3, min_delay_between_jobs=0.0)
    )

    # Events to signal that tasks have entered the critical section.
    entered_a = asyncio.Event()
    entered_b = asyncio.Event()

    async def long_job(name: str, entered: asyncio.Event):
        async with limiter.acquire(name):
            entered.set()
            await asyncio.sleep(0.2)

    # Start two jobs and wait until both are actively running inside the context.
    t1 = asyncio.create_task(long_job("A", entered_a))
    t2 = asyncio.create_task(long_job("B", entered_b))
    await asyncio.wait_for(asyncio.gather(entered_a.wait(), entered_b.wait()), timeout=1.0)

    # While both jobs are running, stats should reflect 2 active and 1 available slot.
    stats_live = limiter.get_stats()
    assert stats_live["current_active_jobs"] == 2
    assert stats_live["available_slots"] == 1

    # Wait for jobs to finish.
    await asyncio.gather(t1, t2)

    # After completion, all slots must be free and registry empty.
    stats_idle = limiter.get_stats()
    assert stats_idle["current_active_jobs"] == 0
    assert stats_idle["available_slots"] == 3

    # Reset should be a no-op functionally now, but must not raise and leaves a clean state.
    limiter.reset()
    stats_after_reset = limiter.get_stats()
    assert stats_after_reset["current_active_jobs"] == 0
    assert stats_after_reset["available_slots"] == 3


def test_load_limiter_config_uses_yaml_values(monkeypatch):
    """Ensure YAML values populate the limiter config."""
    import config.config as config_module

    class Loader:
        @staticmethod
        def load_config():
            return {
                "global_concurrency_limiter": {
                    "max_concurrent_jobs": 7,
                    "min_delay_between_jobs": 1.5,
                }
            }

    monkeypatch.setattr(config_module, "ConfigLoader", Loader)

    cfg = _load_limiter_config()
    assert cfg.max_concurrent_jobs == 7
    assert cfg.min_delay_between_jobs == 1.5


def test_load_limiter_config_falls_back_to_defaults(monkeypatch):
    """If config section missing or invalid, defaults should apply."""
    import config.config as config_module

    class Loader:
        @staticmethod
        def load_config():
            return {}  # Missing section triggers fallback

    monkeypatch.setattr(config_module, "ConfigLoader", Loader)

    cfg = _load_limiter_config()
    defaults = ConcurrencyLimitConfig()
    assert cfg.max_concurrent_jobs == defaults.max_concurrent_jobs
    assert cfg.min_delay_between_jobs == defaults.min_delay_between_jobs


def test_load_limiter_config_sanitizes_invalid_values(monkeypatch):
    """Negative/zero values are sanitized back to safe defaults."""
    import config.config as config_module

    class Loader:
        @staticmethod
        def load_config():
            return {
                "global_concurrency_limiter": {
                    "max_concurrent_jobs": 0,  # invalid
                    "min_delay_between_jobs": -4.2,  # invalid
                }
            }

    monkeypatch.setattr(config_module, "ConfigLoader", Loader)

    cfg = _load_limiter_config()
    defaults = ConcurrencyLimitConfig()
    assert cfg.max_concurrent_jobs == defaults.max_concurrent_jobs
    assert cfg.min_delay_between_jobs == defaults.min_delay_between_jobs
