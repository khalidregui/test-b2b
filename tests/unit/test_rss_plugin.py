"""Unit tests for RSS plugin."""

from __future__ import annotations

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pydantic import ValidationError

from backend.services.scrapping.base_plugin import Event
from backend.services.scrapping.plugins.rss import RSSPlugin
from config.config import SourceConfig


class TestRSSPlugin:
    """Test suite for RSS plugin functionality."""

    @pytest.fixture
    def plugin(self) -> RSSPlugin:
        """Fixture to instantiate an RSS plugin with dummy config."""
        config = SourceConfig(
            name="rss_test",
            plugin_type="rss",
            config_dict={"urls": ["https://techcrunch.com/feed/", "https://thenextweb.com/feed/"]},
        )
        return RSSPlugin(config)

    def test_plugin_rejects_invalid_config(self):
        """Verify invalid configuration raises ValidationError."""
        with pytest.raises(ValidationError):
            invalid_config = SourceConfig(
                name="rss_invalid",
                plugin_type="rss",
                config_dict={"urls": []},  # Empty URLs list should fail
            )
            RSSPlugin(invalid_config)

    @pytest.mark.asyncio
    async def test_fetch_happy_path(self, plugin: RSSPlugin, monkeypatch: MonkeyPatch):
        """
        Exercise the full happy-flow to verify that fetch method correctly
        orchestrates the RSS scraping workflow.

            - Processes all RSS feeds in parallel
            - Extracts articles from each feed
            - Aggregates results into a single list
        """

        # Track calls to verify parallel processing
        calls = []

        # Mock RSS feed processing - now returns Event objects
        async def fake_process_rss_feed(_plugin, url: str):
            calls.append(url)
            # Return mock Event objects based on URL
            if "techcrunch" in url:
                return [
                    Event(
                        source="rss",
                        source_type="rss_test",
                        title="TechCrunch Article 1",
                        text="Tech news summary",
                        url="https://techcrunch.com/article1",
                        published_at=None,
                        profile_data=None,
                    )
                ]
            if "thenextweb" in url:
                return [
                    Event(
                        source="rss",
                        source_type="rss_test",
                        title="TNW Article 1",
                        text="Web tech summary",
                        url="https://thenextweb.com/article1",
                        published_at=None,
                        profile_data=None,
                    )
                ]
            return []

        # Apply monkeypatch
        monkeypatch.setattr(RSSPlugin, "_process_rss_feed", fake_process_rss_feed)

        # Execute test: run fetch method
        result = await plugin.fetch({})

        # Verify both URLs were processed
        assert len(calls) == 2
        assert "techcrunch.com" in calls[0] or "techcrunch.com" in calls[1]
        assert "thenextweb.com" in calls[0] or "thenextweb.com" in calls[1]

        # Verify aggregated results
        assert len(result) == 2  # One article from each feed

        # Check Event structure
        for event in result:
            assert isinstance(event, Event)
            assert event.source == "rss"
            assert event.source_type == "rss_test"
            assert event.title is not None
            assert event.text is not None
            assert event.url is not None
            assert event.profile_data is None

    @pytest.mark.asyncio
    async def test_fetch_handles_feed_errors(self, plugin: RSSPlugin, monkeypatch: MonkeyPatch):
        """Verify graceful handling when one RSS feed fails."""

        async def mock_process_rss_feed(_plugin, url: str):
            if "techcrunch" in url:
                # Simulate successful feed
                return [
                    Event(
                        source="rss",
                        source_type="rss_test",
                        title="Working Article",
                        text="Working content",
                        url="https://techcrunch.com/working",
                        published_at=None,
                        profile_data=None,
                    )
                ]
            # Simulate feed error
            raise Exception("Feed unavailable")

        monkeypatch.setattr(RSSPlugin, "_process_rss_feed", mock_process_rss_feed)

        result = await plugin.fetch({})

        # Verify it doesn't crash and returns partial results
        assert len(result) == 1
        assert isinstance(result[0], Event)
        assert result[0].title == "Working Article"
        assert result[0].profile_data is None

    def test_extract_event_data(self, plugin: RSSPlugin):
        """Test event data extraction and HTML cleaning."""

        # Mock feedparser entry object
        class MockEntry:
            title = "Test Article"
            link = "https://example.com/article"
            summary = "<p>Summary with <strong>HTML</strong> tags</p>"
            published = "Mon, 15 Jan 2024 10:00:00 GMT"
            author = "Test Author"

        mock_entry = MockEntry()

        # Execute test
        result = plugin._extract_event_data(mock_entry)

        # Verify extraction and cleaning
        assert isinstance(result, Event)
        assert result.source == "rss"
        assert result.source_type == "rss_test"
        assert result.title == "Test Article"
        assert result.url == "https://example.com/article"
        # HTML cleaned
        assert result.text == "Summary with HTML tags"
        assert result.published_at is not None  # Date should be parsed
        assert result.profile_data is None
