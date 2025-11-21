import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.services.rate_limiters.phantom_buster_rate_limiter import RateLimitConfig, RateLimiter
from backend.services.scrapping.base_plugin import BasePlugin, Event
from backend.services.scrapping.plugin_manager import PluginManager
from config.config import SourceConfig

# ============================================================================
# Linkedin Plugin Configuration Schema (with Pydantic)
# ============================================================================


class PhantomConfig(BaseModel):
    """PhantomBuster agent configuration."""

    url_finder_id: str = Field(..., min_length=1)
    company_scraper_id: str = Field(..., min_length=1)
    activity_extractor_id: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class RateLimitSettings(BaseModel):
    """Rate limiting configuration."""

    max_calls_per_hour: int = Field(default=10, ge=1)
    max_calls_per_day: int = Field(default=50, ge=1)
    min_delay_between_calls: float = Field(default=60.0, ge=0)
    max_concurrent_calls: int = Field(default=1, ge=1)

    model_config = ConfigDict(extra="forbid")


class LinkedInPluginConfig(BaseModel):
    """LinkedIn plugin configuration."""

    api_url: str = Field(...)
    api_key: str = Field(..., min_length=1)
    session_cookie: str = Field(..., min_length=1)
    user_agent: Optional[str] = Field(None)
    number_max_of_posts: int = Field(3)
    phantoms: PhantomConfig
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    model_config = ConfigDict(extra="forbid")

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Ensure API URL is valid and normalized."""
        if not v.startswith("https://"):
            raise ValueError("API URL must start with https://")
        return v.rstrip("/")

    @field_validator("api_key", "session_cookie")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure critical fields are not empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty")
        return stripped


# ============================================================================
# Linkedin Plugin Implementation
# ============================================================================


class LinkedInPluginError(RuntimeError):
    """Raised when the LinkedIn plugin fails to complete an external call."""


@PluginManager.register("linkedin")
class LinkedInPlugin(BasePlugin[LinkedInPluginConfig]):
    """Plugin to extract company data from LinkedIn via PhantomBuster."""

    def _validate_config(self, config_dict: Dict[str, Any]) -> LinkedInPluginConfig:
        """Validate LinkedIn-specific configuration."""
        return LinkedInPluginConfig.model_validate(config_dict)

    def __init__(self, source_config: SourceConfig) -> None:
        """Initialize the LinkedIn plugin with PhantomBuster configuration."""
        super().__init__(source_config)

        # Construct PhantomBuster API endpoint URLs from validated config
        self.launch_url = f"{self.config.api_url}/agents/launch"
        self.fetch_output_url = f"{self.config.api_url}/agents/fetch-output"

        # Setup HTTP headers for PhantomBuster API requests from validated config
        self.headers = {
            "x-phantombuster-key": self.config.api_key,
            "Content-Type": "application/json",
        }

        # Initialize rate limiter
        rate_limit_config = RateLimitConfig(
            max_calls_per_hour=self.config.rate_limit.max_calls_per_hour,
            max_calls_per_day=self.config.rate_limit.max_calls_per_day,
            min_delay_between_calls=self.config.rate_limit.min_delay_between_calls,
            max_concurrent_calls=self.config.rate_limit.max_concurrent_calls,
        )
        self.rate_limiter = RateLimiter(rate_limit_config)

        logger.info(
            f"Rate limiter initialized: {self.config.rate_limit.max_calls_per_hour} "
            f"calls/hour, {self.config.rate_limit.max_calls_per_day} calls/day, "
            f"max {self.config.rate_limit.max_concurrent_calls} concurrent"
        )

    async def fetch(self, arguments: Dict[str, Any]) -> List[Event]:
        """Execute LinkedIn scraping pipeline for a company.

        Args:
            arguments: Dictionary containing:
                - company_name (str): Company name to search for.
                - city (str): City where the company is located.
                - fetch_posts (bool): Whether to fetch posts. Default: False.
                - fetch_profile (bool): Whether to fetch profile. Default: True.
        """
        # Extract arguments from the dictionary
        company_name = arguments["company_name"]
        city = arguments["city"]
        fetch_posts = arguments.get("fetch_posts", False)
        fetch_profile = arguments.get("fetch_profile", True)

        # Step 1: Find LinkedIn URL
        url = await self.fetch_url(company_name, city)
        if not url:
            logger.warning(f"No LinkedIn URL found for '{company_name}' in '{city}'")
            # Return an empty list of events to respect the method signature
            return []

        # Step 2: Fetch profile if requested
        profile_data = None
        if fetch_profile:
            logger.info(f"Fetching profile data for: {url}")
            profile_data = await self.fetch_profile(url)

        # Step 3: Fetch posts if requested
        posts: List[dict] = []
        if fetch_posts:
            logger.info(f"Fetching posts for: {url}")
            fetched_posts = await self.fetch_posts(url)
            # Coerce to list to avoid iterating over None
            posts = fetched_posts or []
        else:
            posts = [
                {
                    "author": "No posts found",
                    "postContent": "No posts found",
                    "postUrl": "No posts found",
                }
            ]

        events: List[Event] = []
        for p in posts:
            try:
                event = Event(
                    source="linkedin",
                    source_type="company news",
                    title=p.get("author"),
                    text=p.get("postContent", ""),
                    url=p.get("postUrl"),
                    published_at=(
                        datetime.fromisoformat(p["postTimestamp"].replace("Z", "+00:00"))
                        if p.get("postTimestamp")
                        else None
                    ),
                    profile_data=profile_data,
                )
                events.append(event)
            except Exception as e:
                logger.error(f"Error processing post: {e}")

        return events

    # Helper functions
    async def fetch_url(self, company_name: str, city: str) -> Optional[str]:
        """Find a company's LinkedIn URL using its business name and city."""
        arguments = {
            "csvName": "result",
            "spreadsheetUrl": f"{company_name} {city}",
            "numberOfLinesToProcess": 1,
            "sessionCookie": self.config.session_cookie,
            "userAgent": self.config.user_agent,
        }

        logger.info(f"Launching phantom for '{company_name}' in '{city}'...")
        try:
            result = await self.launch_and_fetch_phantom_result(
                self.config.phantoms.url_finder_id, arguments
            )
        except LinkedInPluginError:
            raise
        except Exception as exc:  # pragma: no cover - guard for unexpected runtime failures
            logger.exception(
                "Unexpected error while fetching LinkedIn URL for '%s' in '%s'", company_name, city
            )
            raise LinkedInPluginError("Failed to retrieve LinkedIn URL") from exc

        if not result:
            logger.info("No result found.")
            return None

        try:
            first_row = result[0]
        except (IndexError, TypeError) as exc:
            logger.error("Invalid payload format while reading LinkedIn URL: %s", exc)
            raise LinkedInPluginError("Invalid response format when fetching LinkedIn URL") from exc

        linkedin_url = first_row.get("linkedinUrl") if isinstance(first_row, dict) else None

        if not linkedin_url:
            logger.info("No URL found.")
            return None

        return linkedin_url

    async def fetch_profile(self, url: str) -> Optional[dict]:
        """Extract profiling information using the found URL."""
        arguments = {
            "companiesPerLaunch": 1,
            "delayBetween": 2,
            "spreadsheetUrl": url,
            "sessionCookie": self.config.session_cookie,
            "userAgent": self.config.user_agent,
            "saveImg": False,
        }

        logger.info(f"Launching phantom for URL: '{url}'...")
        try:
            result = await self.launch_and_fetch_phantom_result(
                self.config.phantoms.company_scraper_id, arguments
            )
        except LinkedInPluginError:
            raise
        except Exception as exc:  # pragma: no cover - guard for unexpected runtime failures
            logger.exception("Unexpected error while fetching LinkedIn profile for '%s'", url)
            raise LinkedInPluginError("Failed to retrieve LinkedIn profile") from exc

        if not result:
            logger.info("No result found.")
            return None

        try:
            profile_data = result[0]
        except (IndexError, TypeError) as exc:
            logger.error("Invalid payload format while reading LinkedIn profile: %s", exc)
            raise LinkedInPluginError(
                "Invalid response format when fetching LinkedIn profile"
            ) from exc

        if not profile_data:
            logger.info("No profiling info found.")
            return None

        if not isinstance(profile_data, dict):
            raise LinkedInPluginError("Unexpected profile payload type from PhantomBuster")

        return profile_data

    async def fetch_posts(self, url: str) -> Optional[List[dict]]:
        """Fetch recent LinkedIn posts for an organization."""
        arguments = {
            "numberOfLinesPerLaunch": 1,
            "numberMaxOfPosts": self.config.number_max_of_posts,
            "csvName": "result",
            "activitiesToScrape": ["Post"],
            "spreadsheetUrl": url,
            "sessionCookie": self.config.session_cookie,
            "userAgent": self.config.user_agent,
        }

        logger.info(f"Launching phantom for URL: '{url}' to extract company activities...")
        try:
            result = await self.launch_and_fetch_phantom_result(
                self.config.phantoms.activity_extractor_id, arguments
            )
        except LinkedInPluginError:
            raise
        except Exception as exc:  # pragma: no cover - guard for unexpected runtime failures
            logger.exception("Unexpected error while fetching LinkedIn posts for '%s'", url)
            raise LinkedInPluginError("Failed to retrieve LinkedIn posts") from exc

        if not result:
            logger.info("No result found.")
            return None

        if not isinstance(result, list):
            raise LinkedInPluginError("Unexpected posts payload type from PhantomBuster")

        return result

    async def launch_and_fetch_phantom_result(self, phantom_id: str, arguments: dict) -> dict:
        """Generic helper that launches a PhantomBuster agent and retrieves its JSON output.

        Originally created to avoid duplicating PhantomBuster logic across
        fetch_url(), fetch_profile(), and fetch_posts().

        IMPORTANT: Uses rate limiter context manager to ensure semaphore
        is held for the ENTIRE duration of the API call.
        """
        async with self.rate_limiter.acquire(phantom_id):
            # Log current usage stats
            stats = self.rate_limiter.get_stats(phantom_id)
            global_stats = self.rate_limiter.get_global_stats()

            logger.info(
                f"Rate limit stats - {phantom_id}: "
                f"{stats['hour']}/h, {stats['day']}/day | "
                f"Global: {global_stats['total_calls_last_hour']}/h, "
                f"{global_stats['total_calls_last_day']}/day"
            )

            # Set a timeout for HTTP requests (to prevent hanging)
            default_timeout = aiohttp.ClientTimeout(total=10)

            # Prepare the payload containing the Phantom ID and its launch arguments
            payload = {"id": phantom_id, "arguments": arguments}

            # Step 1: Launch the PhantomBuster agent via POST request
            try:
                async with aiohttp.ClientSession(timeout=default_timeout) as session:
                    async with session.post(
                        self.launch_url, headers=self.headers, json=payload, ssl=False
                    ) as resp:
                        resp.raise_for_status()  # Raise error if the request failed
                        launch_resp = await resp.json()  # Parse the JSON response
            except asyncio.TimeoutError as exc:
                logger.error("Timeout launching PhantomBuster agent '%s': %s", phantom_id, exc)
                raise LinkedInPluginError("Timed out while launching PhantomBuster agent") from exc
            except aiohttp.ClientError as exc:
                logger.error("HTTP error launching PhantomBuster agent '%s': %s", phantom_id, exc)
                raise LinkedInPluginError("HTTP error while launching PhantomBuster agent") from exc

            # Extract the launch container ID returned by PhantomBuster
            launch_response_id = launch_resp.get("containerId")
            if not launch_response_id:
                raise LinkedInPluginError(
                    "Unable to launch PhantomBuster agent: missing containerId"
                )

            logger.info(f"Phantom launched with ID: {launch_response_id}")
            logger.info("Waiting for result...")

            # Step 2: Poll PhantomBuster until the job result becomes available
            result = None
            for attempt in range(30):
                # Query the PhantomBuster output endpoint
                try:
                    async with aiohttp.ClientSession(timeout=default_timeout) as session:
                        async with session.get(
                            self.fetch_output_url,
                            headers=self.headers,
                            params={"id": phantom_id},
                            ssl=False,
                        ) as r:
                            r.raise_for_status()
                            out = await r.json()
                except asyncio.TimeoutError as exc:
                    logger.warning(
                        "Timeout polling PhantomBuster output for '%s' (attempt %s): %s",
                        phantom_id,
                        attempt + 1,
                        exc,
                    )
                    await asyncio.sleep(5)
                    continue
                except aiohttp.ClientError as exc:
                    logger.error(
                        "HTTP error polling PhantomBuster output '%s': %s", phantom_id, exc
                    )
                    raise LinkedInPluginError(
                        "HTTP error while polling PhantomBuster output"
                    ) from exc

                # Check if the output contains a link to the result JSON
                if out and "output" in out:
                    log_output = out["output"]
                    json_match = re.search(r"https://\S+result\.json", log_output)
                    if json_match:
                        json_url = json_match.group(0)
                        logger.info(f"Result found! Downloading from: {json_url}")

                        # Step 3: Download the actual JSON result from the provided URL
                        try:
                            async with aiohttp.ClientSession(timeout=default_timeout) as session:
                                async with session.get(json_url, ssl=False) as result_resp:
                                    result_resp.raise_for_status()
                                    result = await result_resp.json()
                                    logger.info("JSON result downloaded successfully.")
                                    break  # Exit polling loop once result is obtained
                        except asyncio.TimeoutError as exc:
                            logger.warning(
                                "Timeout downloading PhantomBuster result for '%s': %s",
                                phantom_id,
                                exc,
                            )
                            await asyncio.sleep(5)
                            continue
                        except aiohttp.ClientError as exc:
                            logger.error(
                                "HTTP error downloading PhantomBuster result '%s': %s",
                                phantom_id,
                                exc,
                            )
                            raise LinkedInPluginError(
                                "HTTP error while downloading PhantomBuster result"
                            ) from exc

                # Wait 5 seconds before retrying if no result yet
                logger.debug(f"[{attempt + 1}] No result yet — retrying in 5s...")
                await asyncio.sleep(5)

            if result is None:
                logger.error(
                    "PhantomBuster agent '%s' completed without producing a result.", phantom_id
                )

            # Return the parsed JSON result (or None if not found)
            # Le semaphore se libère automatiquement ici à la sortie du 'async with'
            return result
