import asyncio
import html
import re
from typing import Any, Dict, List

import aiohttp
import feedparser
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from backend.services.scrapping.base_plugin import BasePlugin, Event
from backend.services.scrapping.plugin_manager import PluginManager
from config.config import SourceConfig


class RSSPluginConfig(BaseModel):
    """RSS plugin configuration schema."""

    urls: List[HttpUrl] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("urls")
    @classmethod
    def validate_urls_not_empty(cls, v: List[HttpUrl]) -> List[HttpUrl]:
        """Ensure RSS URLs list is not empty."""
        if not v:
            raise ValueError("RSS URLs list cannot be empty")
        return v


@PluginManager.register("rss")
class RSSPlugin(BasePlugin[RSSPluginConfig]):
    """Plugin to aggregate RSS feeds and extract articles."""

    def _validate_config(self, config_dict: Dict[str, Any]) -> RSSPluginConfig:
        """Validate RSS-specific configuration using Pydantic."""
        return RSSPluginConfig.model_validate(config_dict)

    def __init__(self, source_config: SourceConfig):
        """Initialize RSS plugin with validated configuration."""
        super().__init__(source_config)

        # Convert validated HttpUrl objects to strings for HTTP requests
        self.urls = [str(url) for url in self.config.urls]
        logger.info(f"RSS Plugin initialized with {len(self.urls)} feeds")

    async def fetch(self, arguments: Dict[str, Any]) -> List[Event]:
        """Retrieve and aggregate articles from all RSS feeds in parallel."""
        _ = arguments  # Suppress unused argument warning
        logger.info(f"Fetching RSS feeds from {self.name}...")

        # Create parallel tasks for all RSS feed URLs
        tasks = [self._process_rss_feed(url) for url in self.urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results from all feeds
        all_events = []
        for i, result in enumerate(results):
            url = self.urls[i]
            if isinstance(result, Exception):
                # Log error but continue processing other feeds
                logger.error(f"Error processing RSS feed {url}: {result}")
            else:
                # Extend events list with successful results
                all_events.extend(result)
                logger.info(f"Successfully extracted {len(result)} articles from {url}")

        logger.info(f"RSS extraction completed. Total articles: {len(all_events)}")
        return all_events

    async def _process_rss_feed(self, url: str) -> List[Event]:
        """Process a single RSS feed and extract all articles."""
        try:
            logger.info(f"Processing RSS feed: {url}")

            # Download RSS feed content asynchronously with timeout
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30), ssl=False
                ) as response:
                    response.raise_for_status()
                    content = await response.text()

            # Parse RSS/Atom feed using feedparser library
            feed = feedparser.parse(content)

            # Check if feed contains any entries
            if not feed.entries:
                logger.warning(f"No articles found in RSS feed: {url}")
                return []

            # Extract article data from each feed entry
            events = []
            for entry in feed.entries:
                event = self._extract_event_data(entry)
                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Error processing RSS feed {url}: {e}")
            raise

    def _extract_event_data(self, entry) -> Event:
        """Extract and clean article data from a single RSS entry."""
        # Extract basic article information with fallback defaults
        title = getattr(entry, "title", "No title")
        link = getattr(entry, "link", "")
        summary = getattr(entry, "summary", "No summary available")

        # Clean HTML tags from summary using regex
        clean_summary = re.sub("<[^<]+?>", "", summary)
        clean_summary = html.unescape(clean_summary.strip())

        # Extract optional metadata fields
        published_str = getattr(entry, "published", "")
        published_at = None
        if published_str:
            try:
                # Try to parse the published date
                from email.utils import parsedate_to_datetime

                published_at = parsedate_to_datetime(published_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse date: {published_str}")

        # Create Event object with RSS-specific data
        return Event(
            source="rss",
            source_type=self.name,  # Will be "Sectorial context rss" or "cybersecurity context rss"
            title=title,
            text=clean_summary,
            url=link,
            published_at=published_at,
            profile_data=None,  # RSS doesn't have profile data
        )
