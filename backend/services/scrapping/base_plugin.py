from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

from config.config import SourceConfig

# ============================================================================
# Base Plugin Scraping Output Schema (with Pydantic)
# ============================================================================


class Event(BaseModel):
    """Base model output."""

    source: str  # "linkedin", "rss" ...  etc.
    source_type: str  # "company news", "sectorial news", "cybersecurity news"

    # For text content (posts, articles ...)
    title: Optional[str] = None
    text: str = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None

    # For profiling data
    profile_data: Optional[Dict[str, Any]] = None


# ============================================================================
# Base Plugin Implementation
# ============================================================================

ConfigType = TypeVar("ConfigType", bound=BaseModel)


class BasePlugin(ABC, Generic[ConfigType]):
    """Base class for all scrapers. (A contract that all plugins must follow)."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self.name = config.name

        # Validate and convert config_dict to typed configuration
        self.config: ConfigType = self._validate_config(config.config_dict)

    @abstractmethod
    def _validate_config(self, config_dict: dict) -> ConfigType:
        """Each plugin MUST validate its config."""
        pass

    @abstractmethod
    async def fetch(self, arguments: Dict[str, Any]) -> List[Event]:
        """Retrieve raw data from the source."""
        pass
