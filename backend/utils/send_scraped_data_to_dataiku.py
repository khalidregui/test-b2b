"""Data pipeline for scraping and writing to Dataiku.

This module handles the extraction of scraped data from various sources,
transforms it into a standardized DataFrame, and writes it to Dataiku.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import pandas as pd
from dataikuapi import DSSClient
from omegaconf import OmegaConf
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Schema definition
DATAFRAME_COLUMNS = [
    "source",
    "source_type",
    "title",
    "text",
    "url",
    "published_at",
    "profile_data",
    "error",
]


@dataclass
class DataikuConfig:
    """Configuration parameters for Dataiku connection."""

    dss_url: str
    api_key: str
    project_key: str
    dataset_name: str

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
          ValueError: If any configuration parameter is empty.
        """
        if not all([self.dss_url, self.api_key, self.project_key, self.dataset_name]):
            raise ValueError("All configuration parameters must be non-empty")


class ConfigLoader:
    """Load and validate configuration from YAML files using OmegaConf."""

    @staticmethod
    def load_dataiku_config(config_path: str = "config/config.yaml") -> DataikuConfig:
        """Load Dataiku configuration from YAML file.

        Args:
          config_path: Path to the YAML configuration file.

        Returns:
          DataikuConfig instance with validated parameters.

        Raises:
          FileNotFoundError: If config file does not exist.
          KeyError: If required Dataiku configuration is missing.
          ValueError: If configuration parameters are invalid.
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        logger.info(f"Loading configuration from {config_path}")

        try:
            cfg = OmegaConf.load(config_file)
            OmegaConf.resolve(cfg)

            dataiku_config = cfg.get("dataiku")
            if not dataiku_config:
                raise KeyError("Missing 'dataiku' section in configuration")

            return DataikuConfig(
                dss_url=dataiku_config["dss_url"],
                api_key=dataiku_config["api_key"],
                project_key=dataiku_config["project_key"],
                dataset_name=dataiku_config["dataset_name"],
            )
        except (KeyError, TypeError) as e:
            logger.error(f"Invalid configuration structure: {e}")
            raise


class DataikuClient:
    """Manages connection and operations with Dataiku."""

    def __init__(self, config: DataikuConfig):
        """Initialize Dataiku client.

        Args:
          config: DataikuConfig instance with connection parameters.
        """
        self.config = config
        self._client = None
        self._project = None

    def connect(self) -> None:
        """Establish connection to Dataiku and validate project access.

        Raises:
          Exception: If connection fails or project is not accessible.
        """
        try:
            logger.info(f"Connecting to Dataiku at {self.config.dss_url}...")
            self._client = DSSClient(self.config.dss_url, self.config.api_key)

            self._project = self._client.get_project(self.config.project_key)
            project_label = self._project.get_metadata()["label"]
            logger.info(f"Successfully connected to project: {project_label}")
        except Exception as e:
            logger.error(f"Failed to connect to Dataiku: {e}")
            raise

    def write_dataframe(self, dataframe: pd.DataFrame) -> None:
        """Write DataFrame to Dataiku dataset.

        Args:
          dataframe: DataFrame to write.

        Raises:
          RuntimeError: If not connected or write operation fails.
        """
        if self._project is None:
            raise RuntimeError("Not connected to Dataiku. Call connect() first.")

        if dataframe.empty:
            logger.warning("Attempted to write empty DataFrame")
            return

        try:
            dataset = self._project.get_dataset(self.config.dataset_name)
            core_dataset = dataset.get_as_core_dataset()
            core_dataset.write_with_schema(dataframe)
            logger.info(f"Successfully wrote {len(dataframe)} rows to {self.config.dataset_name}")
        except Exception as e:
            logger.error(f"Failed to write data to Dataiku: {e}")
            raise


def _event_to_row(source_name: str, event: Any) -> Dict[str, Any]:
    """Convert a plugin event into a standardized row dictionary.

    Handles Pydantic models, dictionaries, and other types. Missing fields
    are filled with None to maintain consistent schema.

    Args:
      source_name: Name of the data source.
      event: Event data (Pydantic model, dict, or other).

    Returns:
      Dictionary with standardized column structure.
    """
    if isinstance(event, BaseModel):
        data = event.model_dump()
    elif isinstance(event, Mapping):
        data = dict(event)
    else:
        data = {"text": str(event)}

    profile = data.get("profile_data")
    if isinstance(profile, dict):
        profile = json.dumps(profile)

    return {
        "source": data.get("source") or source_name,
        "source_type": data.get("source_type"),
        "title": data.get("title"),
        "text": data.get("text"),
        "url": data.get("url"),
        "published_at": data.get("published_at"),
        "profile_data": profile,
        "error": None,
    }


def pipeline_results_to_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
    """Convert pipeline output to a normalized DataFrame.

    Transforms the output from multiple data sources into a single tidy
    DataFrame. Each row represents one scraped event. Error states are
    preserved as rows with error messages.

    Args:
      results: Dictionary mapping source names to their output (events,
        lists of events, or error objects).

    Returns:
      DataFrame with standardized schema defined in DATAFRAME_COLUMNS.
    """
    rows: List[Dict[str, Any]] = []

    for plugin_name, payload in results.items():
        # Handle error responses
        if isinstance(payload, Mapping) and "error" in payload:
            rows.append(
                {
                    "source": plugin_name,
                    "source_type": None,
                    "title": None,
                    "text": None,
                    "url": None,
                    "published_at": None,
                    "profile_data": None,
                    "error": payload.get("error"),
                }
            )
            continue

        # Handle sequences of events
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            for event in payload:
                rows.append(_event_to_row(plugin_name, event))
            continue

        # Handle single event
        if payload is not None:
            rows.append(_event_to_row(plugin_name, payload))

    if not rows:
        return pd.DataFrame(columns=DATAFRAME_COLUMNS)

    return pd.DataFrame(rows, columns=DATAFRAME_COLUMNS)


def main(config: DataikuConfig) -> None:
    """Main pipeline orchestration.

    Args:
      config: DataikuConfig instance with connection parameters.
    """
    client = DataikuClient(config)
    client.connect()

    # TODO: Replace with actual pipeline execution
    pipeline_output = {
        "linkedin": [
            {
                "source": "linkedin",
                "source_type": "company_news",
                "title": "Ouverture d'un nouveau hub",
                "text": "Nous inaugurons un hub à Casablanca.",
                "url": "https://linkedin.com/posts/123",
                "published_at": datetime(2024, 2, 12),
            },
        ],
        "rss": {"error": "HTTP 500"},
    }

    dataframe = pipeline_results_to_dataframe(pipeline_output)
    client.write_dataframe(dataframe)


# def send_scraped_data_to_dataiku():
#     try:
#         config = ConfigLoader.load_dataiku_config("config/config.yaml")
#         client = DataikuClient(config)
#         client.connect()
#         pipeline_output = run_pipeline("config/config.yaml", company_name="", city="")
#         dataframe = pipeline_results_to_dataframe(pipeline_output)
#         client.write_dataframe(dataframe)

# except (FileNotFoundError, KeyError, ValueError) as e:
#     logger.error(f"Configuration error: {e}")
#     raise


if __name__ == "__main__":
    try:
        config = ConfigLoader.load_dataiku_config("config/config.yaml")
        main(config)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
        raise
