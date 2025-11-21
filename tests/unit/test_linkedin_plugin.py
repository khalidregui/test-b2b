"""Unit tests for LinkedIn plugin."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pydantic import ValidationError

from backend.services.scrapping.plugins.linkedin import LinkedInPlugin
from config.config import SourceConfig


class TestLinkedInPlugin:
    """Test suite for LinkedIn plugin functionality."""

    @pytest.fixture
    def plugin(self) -> LinkedInPlugin:
        """Fixture to instantiate a linkedin plugin with dummy config."""
        config = SourceConfig(
            name="linkedin",
            plugin_type="linkedin",
            config_dict={
                "api_url": "https://phantombuster.test/api/v2",
                "api_key": "dummy-key",
                "user_agent": "pytest-agent",
                "session_cookie": "dummy-cookie",
                "phantoms": {
                    "url_finder_id": "finder-id",
                    "company_scraper_id": "scraper-id",
                    "activity_extractor_id": "activity-id",
                },
            },
        )
        return LinkedInPlugin(config)

    def test_plugin_rejects_invalid_config(self):
        """Verify invalid configuration raises ValidationError."""
        with pytest.raises(ValidationError):
            invalid_config = SourceConfig(
                name="linkedin", plugin_type="linkedin", config_dict={"api_url": "http://bad.com"}
            )
            LinkedInPlugin(invalid_config)

    @pytest.mark.asyncio
    async def test_fetch_happy_path(self, plugin: LinkedInPlugin, monkeypatch: MonkeyPatch):
        """
        Exercise the full happy-flow to verify that fetch method correctly
        orchestrates the scraping workflow.

            - Extracts arguments correctly
            - Calls fetch_url with company_name and city
            - Passes the returned URL to fetch_profile and fetch_posts
            - Aggregates results into the expected structure
        """

        # Track call order
        calls = []

        # Setup monkeypatchs to mock fetching helper functions (to void external calls)
        async def fake_fetch_url(_plugin, company_name: str, city: str) -> str:
            calls.append(("fetch_url", company_name, city))
            return "https://linkedin.com/company/artefact"

        async def fake_fetch_profile(_plugin, url: str):
            calls.append(("fetch_profile", url))
            return {"name": "Artefact", "linkedinUrl": url}

        async def fake_fetch_posts(_plugin, url: str):
            calls.append(("fetch_posts", url))
            return [
                {
                    "author": "Artefact",
                    "postContent": "We just shipped a new feature!",
                    "postUrl": "https://linkedin.com/posts/1",
                    "postTimestamp": "2024-10-20T12:34:56Z",
                }
            ]

        # Apply monkeypatchs
        monkeypatch.setattr(LinkedInPlugin, "fetch_url", fake_fetch_url)
        monkeypatch.setattr(LinkedInPlugin, "fetch_profile", fake_fetch_profile)
        monkeypatch.setattr(LinkedInPlugin, "fetch_posts", fake_fetch_posts)

        # Execute test : execute fetch method with the complete argument payload
        result = await plugin.fetch(
            {
                "company_name": "Artefact",
                "city": "Casablanca",
                "fetch_profile": True,
                "fetch_posts": True,
            }
        )

        # Verify order and arguments
        assert calls[0] == ("fetch_url", "Artefact", "Casablanca")
        assert calls[1] == ("fetch_profile", "https://linkedin.com/company/artefact")
        assert calls[2] == ("fetch_posts", "https://linkedin.com/company/artefact")

        # Assert: events are built from posts with embedded profile_data
        assert isinstance(result, list)
        assert len(result) == 1
        event = result[0]
        assert event.source == "linkedin"
        assert event.source_type == "company news"
        assert event.title == "Artefact"
        assert event.text == "We just shipped a new feature!"
        assert event.url == "https://linkedin.com/posts/1"
        # Published at is parsed with 'Z' treated as UTC
        assert event.published_at == datetime(2024, 10, 20, 12, 34, 56, tzinfo=timezone.utc)
        assert event.profile_data == {
            "name": "Artefact",
            "linkedinUrl": "https://linkedin.com/company/artefact",
        }

    @pytest.mark.asyncio
    async def test_fetch_handles_missing_url(self, plugin, monkeypatch):
        """Verify graceful handling when LinkedIn URL is not found (returns empty list)."""

        async def mock_fetch_url(_plugin, _company_name, _city):
            return None  # Simule "URL non trouvée"

        monkeypatch.setattr(LinkedInPlugin, "fetch_url", mock_fetch_url)

        result = await plugin.fetch(
            {
                "company_name": "Unknown",
                "city": "Nowhere",
            }
        )

        # Verify it doesn't crash and returns an empty list of events
        assert isinstance(result, list)
        assert result == []
