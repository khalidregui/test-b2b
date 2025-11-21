from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from omegaconf import OmegaConf

# load_dotenv()


@dataclass
class SourceConfig:
    """Configuration for a data source."""

    name: str
    plugin_type: str
    config_dict: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class DefaultsConfig:
    """Global default values."""

    api_base_url: str = "https://api.phantombuster.com/api/v2"


@dataclass
class AppConfig:
    """Complete application configuration."""

    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    sources: List[SourceConfig] = field(default_factory=list)


class ConfigLoader:
    """Load and validate the configuration using OmegaConf."""

    @staticmethod
    def load_config(config_path: str = "config/config.yaml") -> AppConfig:
        """Load the YAML file and convert it into a structured AppConfig."""
        # Checks if the file exists
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Loads the YAML
        cfg = OmegaConf.load(config_path)

        # Resolves the interpolations
        OmegaConf.resolve(cfg)

        # Converts to a typed structure

        return OmegaConf.to_object(cfg)

    @staticmethod
    def load_sources(config_path: str = "config/config.yaml") -> List[SourceConfig]:
        """Load only the list of sources."""
        app_config = ConfigLoader.load_config(config_path)
        if hasattr(app_config, "sources"):
            return getattr(app_config, "sources")

        if isinstance(app_config, dict):
            raw_sources = app_config.get("sources", [])
            return [
                SourceConfig(**raw_source)
                for raw_source in raw_sources
                if isinstance(raw_source, dict)
            ]

        raise TypeError("Config object could not be interpreted as AppConfig")
