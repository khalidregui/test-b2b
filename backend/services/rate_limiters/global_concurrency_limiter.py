"""Global concurrency limiter to protect the VM from overload.

This module defines an asynchronous concurrency limiter that ensures
only a limited number of heavy backend tasks
can run simultaneously across all users.

Usage Example:
--------------
    from fastapi import APIRouter, HTTPException
    from backend.services.rate_limiters.global_concurrency_limiter import global_concurrency_limiter

    router = APIRouter()

    @router.post("/generate-company-sheet")
    async def generate_company_sheet(payload: dict):
        try:
            async with global_concurrency_limiter.acquire("generate_company_sheet"):
                result = await generate_sheet_for_company(payload)
                return {"status": "ok", "data": result}
        except asyncio.TimeoutError:
            raise HTTPException(status_code=429, detail="Server is busy, please try again later.")
"""

import asyncio
import time
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger

# ============================================================================
# Configuration Dataclass
# ============================================================================


@dataclass
class ConcurrencyLimitConfig:
    """Configuration for global concurrency control."""

    # Maximum number of concurrent heavy operations allowed at any time
    max_concurrent_jobs: int = 3

    # Optional delay to space out job starts (e.g., 1-2s between jobs)
    min_delay_between_jobs: float = 0.0


# ============================================================================
# Concurrency Limiter Implementation
# ============================================================================


class GlobalConcurrencyLimiter:
    """Global concurrency limiter shared across all API requests.

    Ensures that no more than `max_concurrent_jobs` run in parallel.
    Designed for CPU- or memory-heavy processes (like scraping, analytics).

    The limiter is a singleton created once at FastAPI startup and reused globally.
    """

    def __init__(self, config: ConcurrencyLimitConfig):
        # Store config
        self.config = config

        # Semaphore used to restrict concurrency across all users
        self._semaphore = asyncio.Semaphore(config.max_concurrent_jobs)

        # Optional lock used to enforce delay between consecutive job starts
        self._lock = asyncio.Lock()

        # Job tracking for logging and metrics
        self._active_jobs: Dict[str, float] = {}

        logger.info(
            f"GlobalConcurrencyLimiter initialized: "
            f"max_concurrent_jobs={config.max_concurrent_jobs}, "
            f"min_delay_between_jobs={config.min_delay_between_jobs}s"
        )

    @asynccontextmanager
    async def acquire(self, job_name: str):
        """Async context manager that enforces concurrency limits.

        Steps:
        - Wait for a semaphore slot (limits concurrent jobs)
        - Optionally apply a minimum delay between job starts
        - Record job start time
        - Release automatically on exit
        """
        start_time = time.time()
        await self._semaphore.acquire()  # Block until a slot is free

        try:
            # Log entry
            logger.debug(
                f"Job '{job_name}' started. "
                f"Active jobs: {self._semaphore._value}/{self.config.max_concurrent_jobs}"
            )

            # Optional: enforce delay between consecutive jobs
            async with self._lock:
                if self.config.min_delay_between_jobs > 0:
                    logger.debug(
                        f"Applying {self.config.min_delay_between_jobs:.1f}s delay "
                        f"before starting '{job_name}'"
                    )
                    await asyncio.sleep(self.config.min_delay_between_jobs)

            # Register active job
            self._active_jobs[job_name] = start_time

            # Yield control to the job code
            yield

        finally:
            # Job done → release resources
            self._active_jobs.pop(job_name, None)
            self._semaphore.release()
            duration = time.time() - start_time
            logger.debug(
                f"Job '{job_name}' finished after {duration:.1f}s. "
                f"Remaining slots: {self._semaphore._value}/{self.config.max_concurrent_jobs}"
            )

    def get_stats(self) -> Dict[str, Optional[int]]:
        """Return current statistics on active jobs."""
        return {
            "max_concurrent_jobs": self.config.max_concurrent_jobs,
            "current_active_jobs": len(self._active_jobs),
            "available_slots": self._semaphore._value,
        }

    def reset(self) -> None:
        """Force-clear active job registry (useful for debugging)."""
        self._active_jobs.clear()
        logger.info("🔄 GlobalConcurrencyLimiter state reset.")


# ============================================================================
# Singleton Instance for Global Use
# ============================================================================


def _extract_field(config_section: Any, field_name: str, default_value: Any) -> Any:
    """Return value for `field_name` from dict/obj `config_section` with fallback."""
    if isinstance(config_section, dict):
        return config_section.get(field_name, default_value)
    if hasattr(config_section, field_name):
        return getattr(config_section, field_name, default_value)
    if hasattr(config_section, "get"):
        try:
            return config_section.get(field_name, default_value)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to read '%s' from config section via get(): %s. Using default.",
                field_name,
                exc,
            )
            return default_value
    return default_value


def _load_limiter_config() -> ConcurrencyLimitConfig:
    """Load limiter settings from config.yaml, falling back to safe defaults."""
    default_cfg = ConcurrencyLimitConfig()
    try:
        from config.config import ConfigLoader
        cfg = ConfigLoader.load_config("/app/config/config.yaml")
        logger.info("Config loaded successfully")
    except Exception as exc:
        logger.error(f"Config loading failed - Error type: {type(exc).__name__}")
        logger.error(f"Config loading failed - Error message: {exc}")
        logger.error(f"Config loading failed - Working directory: {os.getcwd()}")
        logger.error(f"Config file exists: {os.path.exists('/app/config/config.yaml')}")
        return default_cfg

    limiter_cfg = None
    if isinstance(cfg, dict):
        limiter_cfg = cfg.get("global_concurrency_limiter")
    else:
        limiter_cfg = getattr(cfg, "global_concurrency_limiter", None)
        if limiter_cfg is None and hasattr(cfg, "get"):
            try:
                limiter_cfg = cfg.get("global_concurrency_limiter")
            except Exception:  # pragma: no cover - defensive
                limiter_cfg = None

    if limiter_cfg is None:
        logger.warning("`global_concurrency_limiter` missing in config.yaml; using defaults.")
        return default_cfg

    max_jobs = int(
        _extract_field(limiter_cfg, "max_concurrent_jobs", default_cfg.max_concurrent_jobs)
    )
    min_delay = float(
        _extract_field(limiter_cfg, "min_delay_between_jobs", default_cfg.min_delay_between_jobs)
    )

    if max_jobs < 1:
        logger.warning(
            "max_concurrent_jobs must be >= 1, got %s. Falling back to %s.",
            max_jobs,
            default_cfg.max_concurrent_jobs,
        )
        max_jobs = default_cfg.max_concurrent_jobs

    if min_delay < 0:
        logger.warning(
            "min_delay_between_jobs must be >= 0, got %s. Falling back to %s.",
            min_delay,
            default_cfg.min_delay_between_jobs,
        )
        min_delay = default_cfg.min_delay_between_jobs

    return ConcurrencyLimitConfig(max_concurrent_jobs=max_jobs, min_delay_between_jobs=min_delay)


# Create a single global instance that can be imported anywhere using config.yaml
global_concurrency_limiter = GlobalConcurrencyLimiter(_load_limiter_config())
