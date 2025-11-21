from typing import ClassVar, Dict, List, Optional

from loguru import logger

from backend.services.scrapping.base_plugin import BasePlugin
from config.config import SourceConfig


class PluginManager:
    """Identify which plugins exist (i.e., the classes).

    where to find them, and how to instantiate them.
    """

    # Storage of plugin classes
    _plugins: ClassVar[Dict[str, type[BasePlugin]]] = {}

    # ==================== REGISTRY: Automatic plugin directory ===================

    @classmethod
    def register(cls, plugin_type: str):
        """Register plugins."""

        def decorator(plugin_class):
            cls._plugins[plugin_type] = plugin_class
            return plugin_class

        return decorator

    @classmethod
    def get_plugin(cls, plugin_type: str) -> type[BasePlugin]:
        """Return a plugin."""
        if cls._plugins is None:
            cls._plugins = {}
        return cls._plugins.get(plugin_type)

    @classmethod
    def list_plugins(cls) -> List[str]:
        """List all registered plugin types."""
        return list(cls._plugins.keys())

    # ==================== FACTORY: Plugin instantiation ====================

    @classmethod
    def create_plugin(cls, source_config: SourceConfig) -> Optional[BasePlugin]:
        """Create a plugin instance from its configuration."""
        # Checks if enabled
        if not source_config.enabled:
            logger.info(f"Plugin '{source_config.name}' disabled")
            return None

        # Retrieves the class
        plugin_class = cls.get_plugin(source_config.plugin_type)

        if not plugin_class:
            available = cls.list_plugins()
            raise ValueError(
                f"Plugin '{source_config.plugin_type}' unknown. Available plugins: {available}"
            )

        # Instantiation
        try:
            return plugin_class(source_config)
        except Exception as e:
            raise Exception(
                f"Error initializing plugin "
                f"'{source_config.name}' ({source_config.plugin_type}): {e}"
            )

    @classmethod
    def create_all(cls, source_configs: List[SourceConfig]) -> List[BasePlugin]:
        """Create multiple plugins from a list of configurations.

        Args:
            source_configs: List of configurations.

        Returns:
            List of successfully created plugins.
        """
        plugins = []

        for config in source_configs:
            try:
                plugin = cls.create_plugin(config)
                if plugin:  # None if disabled
                    plugins.append(plugin)
                    logger.info(f"Plugin '{config.name}' created")
            except Exception as e:
                logger.error(f"Error with '{config.name}': {e}")

        return plugins
