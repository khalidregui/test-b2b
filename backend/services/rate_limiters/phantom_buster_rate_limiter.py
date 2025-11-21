"""Rate limiter for PhantomBuster API calls to prevent account bans."""

import asyncio
import random
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, Optional

from loguru import logger

# ============================================================================
# Data classes for Rate Limiter config and History of Phantom buster API calls
# ============================================================================


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_calls_per_hour: int = 10
    max_calls_per_day: int = 50
    min_delay_between_calls: float = 60.0
    max_concurrent_calls: int = 1
    enable_random_delay: bool = True


@dataclass
class CallRecord:
    """Record of API calls for rate limiting tracking."""

    timestamps: list[float] = field(default_factory=list)
    last_call_time: Optional[float] = None


# ============================================================================
# Rate limiter implementation
# ============================================================================


class RateLimiter:
    """Rate limiter to control PhantomBuster API usage.

    Prevents account bans by:
    - Limiting concurrent calls (globally across all sales team members)
    - Limiting calls per hour and per day
    - Enforcing minimum delays between calls

    Note: FastAPI creates one plugin instance at startup,
    so this rate limiter is automatically shared between all users.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config  # Save rate limit config
        self._records: Dict[str, CallRecord] = {}  # Keep track of call history per phantom
        self._semaphore = asyncio.Semaphore(config.max_concurrent_calls)  # Limit concurrent calls
        self._lock = asyncio.Lock()  # Prevent race conditions when updating records

        logger.info(
            f"Rate limiter initialized: {config.max_calls_per_hour} calls/hour, "
            f"{config.max_calls_per_day} calls/day, "
            f"{config.max_concurrent_calls} concurrent max"
        )

    @asynccontextmanager
    async def acquire(self, phantom_id: str):
        """Context manager that enforces rate limits.

        Usage:
            async with rate_limiter.acquire(phantom_id):
                result = await make_api_call()

        The semaphore is held for the ENTIRE duration of the API call,
        preventing concurrent calls from different users.
        """
        # Step 1: Acquire a semaphore ticket
        await self._semaphore.acquire()
        logger.debug(f"🔒 Semaphore acquired for {phantom_id}")

        try:
            # Step 2: Wait if the rate limit (per hour/day) has been reached.
            await self._wait_for_rate_limit(phantom_id)

            # Step 3:  Record this API call
            await self._record_call(phantom_id)

            # Step 4: Add random 10-30s delay to mimic human behavior and avoid bot detection
            if self.config.enable_random_delay:
                random_delay = random.uniform(10, 30)  # nosec B311
                logger.debug(f"⏱️ Adding random delay of {random_delay:.1f}s")
                await asyncio.sleep(random_delay)

            # Step 5: Yield control back to the calling code.
            yield  # Calling code (the actual API call) runs here

        finally:
            self._semaphore.release()
            logger.debug(f"🔓 Semaphore released for {phantom_id}")

    async def _wait_for_rate_limit(self, phantom_id: str) -> None:
        """Wait until rate limits allow a new call."""
        # Async lock to prevent multiple courotines from modifying self._records at the same time.
        async with self._lock:
            record = self._records.get(phantom_id, CallRecord())
            current_time = time.time()

            # Clean old timestamps (keep only last 24h)
            one_hour_ago = current_time - 3600
            one_day_ago = current_time - 86400
            record.timestamps = [ts for ts in record.timestamps if ts > one_day_ago]

            # Check hourly limit
            recent_calls = [ts for ts in record.timestamps if ts > one_hour_ago]
            if len(recent_calls) >= self.config.max_calls_per_hour:
                wait_time = 3600 - (current_time - recent_calls[0]) + 1
                logger.warning(
                    f"⏳ Hourly limit reached for {phantom_id} "
                    f"({len(recent_calls)}/{self.config.max_calls_per_hour}). "
                    f"Waiting {wait_time:.0f}s..."
                )
                await asyncio.sleep(wait_time)
                # Recursive call to re-check after waiting
                return await self._wait_for_rate_limit(phantom_id)

            # Check daily limit
            if len(record.timestamps) >= self.config.max_calls_per_day:
                wait_time = 86400 - (current_time - record.timestamps[0]) + 1
                logger.warning(
                    f"⏳ Daily limit reached for {phantom_id} "
                    f"({len(record.timestamps)}/{self.config.max_calls_per_day}). "
                    f"Waiting {wait_time / 3600:.1f}h..."
                )
                await asyncio.sleep(wait_time)
                return await self._wait_for_rate_limit(phantom_id)

            # Check minimum delay between calls
            if record.last_call_time:
                elapsed = current_time - record.last_call_time
                if elapsed < self.config.min_delay_between_calls:
                    wait_time = self.config.min_delay_between_calls - elapsed
                    logger.info(
                        f"⏱️ Enforcing minimum delay for {phantom_id}. Waiting {wait_time:.0f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    return None
                return None
            return None

    async def _record_call(self, phantom_id: str) -> None:
        """Record that a call was made."""
        async with self._lock:
            current_time = time.time()

            if phantom_id not in self._records:
                self._records[phantom_id] = CallRecord()

            record = self._records[phantom_id]
            record.timestamps.append(current_time)
            record.last_call_time = current_time

            logger.debug(
                f"✓ Call recorded for {phantom_id}. "
                f"Total calls in last 24h: {len(record.timestamps)}"
            )

    def get_stats(self, phantom_id: str) -> Dict[str, int]:
        """Get usage statistics for a specific phantom.

        Returns:
            Dictionary with call counts for different time periods
        """
        record = self._records.get(phantom_id)
        if not record:
            return {"hour": 0, "day": 0, "total": 0}

        current_time = time.time()
        one_hour_ago = current_time - 3600
        one_day_ago = current_time - 86400

        return {
            "hour": len([ts for ts in record.timestamps if ts > one_hour_ago]),
            "day": len([ts for ts in record.timestamps if ts > one_day_ago]),
            "total": len(record.timestamps),
        }

    def get_global_stats(self) -> Dict[str, int]:
        """Get aggregated statistics for ALL phantoms.

        Useful to see total usage across all sales team members.

        Returns:
            Dictionary with aggregated call counts
        """
        total_hour = 0
        total_day = 0
        total_all = 0

        current_time = time.time()
        one_hour_ago = current_time - 3600
        one_day_ago = current_time - 86400

        for record in self._records.values():
            total_hour += len([ts for ts in record.timestamps if ts > one_hour_ago])
            total_day += len([ts for ts in record.timestamps if ts > one_day_ago])
            total_all += len(record.timestamps)

        return {
            "total_calls_last_hour": total_hour,
            "total_calls_last_day": total_day,
            "total_calls_all_time": total_all,
            "phantoms_tracked": len(self._records),
        }

    def reset(self, phantom_id: Optional[str] = None) -> None:
        """Reset rate limit records.

        Args:
            phantom_id: If provided, reset only this phantom. Otherwise reset all.
        """
        if phantom_id:
            self._records.pop(phantom_id, None)
            logger.info(f"🔄 Rate limit reset for {phantom_id}")
        else:
            self._records.clear()
            logger.info("🔄 All rate limits reset")
