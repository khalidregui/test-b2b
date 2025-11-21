"""Unit tests for rate limiter."""

import asyncio
import time

import pytest

from backend.services.rate_limiters.phantom_buster_rate_limiter import RateLimitConfig, RateLimiter


class TestRateLimiter:
    """Test suite for the RateLimiter class."""

    # ============================================================================
    # Fixtures
    # ============================================================================

    @pytest.fixture
    def base_config(self):
        """Base configuration for tests with random delay disabled."""
        return {
            "max_calls_per_hour": 100,
            "max_calls_per_day": 1000,
            "min_delay_between_calls": 0.0,
            "max_concurrent_calls": 1,
            "enable_random_delay": False,
        }

    # ============================================================================
    # Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_enforces_minimum_delay(self, base_config):
        """Test that minimum delay between calls is enforced."""
        config_dict = base_config.copy()
        config_dict["min_delay_between_calls"] = 0.5
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        start = time.time()

        async with limiter.acquire("test-phantom"):
            pass

        async with limiter.acquire("test-phantom"):
            pass

        elapsed = time.time() - start

        assert elapsed >= 0.5, f"Minimum delay not enforced. Got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_blocks_on_hourly_limit(self, base_config):
        """Test that hourly limit is enforced."""
        config_dict = base_config.copy()
        config_dict.update(
            {
                "max_calls_per_hour": 2,
                "min_delay_between_calls": 0.1,
                "max_concurrent_calls": 5,
            }
        )
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        async with limiter.acquire("test-phantom"):
            pass

        await asyncio.sleep(0.15)

        async with limiter.acquire("test-phantom"):
            pass

        stats = limiter.get_stats("test-phantom")
        assert stats["hour"] == 2, f"Expected 2 calls in last hour, got {stats['hour']}"

    @pytest.mark.asyncio
    async def test_concurrent_limit(self, base_config):
        """Test that concurrent call limit is enforced."""
        config_dict = base_config.copy()
        config_dict["max_concurrent_calls"] = 2
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        concurrent_count = 0
        max_concurrent_seen = 0
        lock = asyncio.Lock()

        async def acquire_and_track(phantom_id: str):
            nonlocal concurrent_count, max_concurrent_seen

            async with limiter.acquire(phantom_id):
                async with lock:
                    concurrent_count += 1
                    max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

                await asyncio.sleep(0.2)

                async with lock:
                    concurrent_count -= 1

        await asyncio.gather(
            acquire_and_track("phantom-1"),
            acquire_and_track("phantom-1"),
            acquire_and_track("phantom-2"),
            acquire_and_track("phantom-2"),
        )

        assert max_concurrent_seen <= 2, (
            f"Expected max 2 concurrent calls, but saw {max_concurrent_seen}"
        )

    @pytest.mark.asyncio
    async def test_stats_tracking(self, base_config):
        """Test that statistics are correctly tracked."""
        config_dict = base_config.copy()
        config_dict["max_concurrent_calls"] = 10
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        stats = limiter.get_stats("test-phantom")
        assert stats["hour"] == 0
        assert stats["day"] == 0
        assert stats["total"] == 0

        async with limiter.acquire("test-phantom"):
            pass

        async with limiter.acquire("test-phantom"):
            pass

        async with limiter.acquire("test-phantom"):
            pass

        stats = limiter.get_stats("test-phantom")
        assert stats["hour"] == 3
        assert stats["day"] == 3
        assert stats["total"] == 3

    @pytest.mark.asyncio
    async def test_reset(self, base_config):
        """Test that reset clears records."""
        config_dict = base_config.copy()
        config_dict["max_concurrent_calls"] = 10
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        async with limiter.acquire("phantom-1"):
            pass

        async with limiter.acquire("phantom-2"):
            pass

        limiter.reset("phantom-1")

        stats1 = limiter.get_stats("phantom-1")
        stats2 = limiter.get_stats("phantom-2")

        assert stats1["total"] == 0
        assert stats2["total"] == 1

        limiter.reset()

        stats2 = limiter.get_stats("phantom-2")
        assert stats2["total"] == 0

    @pytest.mark.asyncio
    async def test_different_phantoms_independent(self, base_config):
        """Test that different phantoms have independent rate limits."""
        config_dict = base_config.copy()
        config_dict.update(
            {
                "min_delay_between_calls": 0.1,
                "max_concurrent_calls": 2,
            }
        )
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        async with limiter.acquire("phantom-1"):
            pass

        async with limiter.acquire("phantom-2"):
            pass

        stats1 = limiter.get_stats("phantom-1")
        stats2 = limiter.get_stats("phantom-2")

        assert stats1["total"] == 1
        assert stats2["total"] == 1

    @pytest.mark.asyncio
    async def test_global_stats(self, base_config):
        """Test that global statistics aggregate correctly."""
        config_dict = base_config.copy()
        config_dict["max_concurrent_calls"] = 10
        config = RateLimitConfig(**config_dict)
        limiter = RateLimiter(config)

        global_stats = limiter.get_global_stats()
        assert global_stats["total_calls_all_time"] == 0

        async with limiter.acquire("phantom-1"):
            pass

        async with limiter.acquire("phantom-1"):
            pass

        async with limiter.acquire("phantom-2"):
            pass

        global_stats = limiter.get_global_stats()
        assert global_stats["total_calls_last_hour"] == 3
        assert global_stats["total_calls_last_day"] == 3
        assert global_stats["total_calls_all_time"] == 3
        assert global_stats["phantoms_tracked"] == 2

    @pytest.mark.asyncio
    async def test_exception_releases_semaphore(self, base_config):
        """Test that semaphore is released even if an exception occurs."""
        config = RateLimitConfig(**base_config)
        limiter = RateLimiter(config)

        try:
            async with limiter.acquire("test-phantom"):
                raise ValueError("Simulated error")
        except ValueError:
            pass

        start = time.time()
        async with limiter.acquire("test-phantom"):
            pass
        elapsed = time.time() - start

        assert elapsed < 0.1, "Semaphore was not released after exception"
