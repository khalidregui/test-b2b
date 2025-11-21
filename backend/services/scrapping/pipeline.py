from typing import Any, Dict, List, Optional

from loguru import logger

from backend.services.scrapping.base_plugin import BasePlugin
from backend.services.scrapping.plugin_manager import PluginManager
from config.config import ConfigLoader


class DataPipeline:
    """Data processing pipeline."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.plugins: List[BasePlugin] = []

    def load_plugins(self) -> None:
        """Load all plugins from the configuration."""
        logger.info("Loading configuration...")

        # Loads the configs from the YAML
        source_configs = ConfigLoader.load_sources(self.config_path)

        # Creates ALL plugins at once using the Manager
        self.plugins = PluginManager.create_all(source_configs)

        logger.info("Loaded {} active plugin(s)", len(self.plugins))

    async def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all plugins."""
        if not self.plugins:
            msg = "Plugins are not loaded. Call load_plugins() before run()."
            raise RuntimeError(msg)

        logger.info("Starting pipeline...")

        results: Dict[str, Any] = {}
        for plugin in self.plugins:
            try:
                logger.info("Execution of '{}'...", plugin.name)
                data = await plugin.fetch(arguments=arguments)
                results[plugin.name] = data
                logger.info("Execution of '{}' completed", plugin.name)
            except Exception as e:
                logger.exception("Execution of '{}' failed: {}", plugin.name, e)
                results[plugin.name] = {"error": str(e)}

        return results

    @staticmethod
    def prepare_arguments(
        company_name: Optional[str] = None,
        city: Optional[str] = None,
        fetch_posts: bool = True,
        fetch_profile: bool = True,
    ) -> Dict[str, Any]:
        """Prepare arguments dictionary for pipeline execution."""
        return {
            "company_name": company_name,
            "city": city,
            "fetch_posts": fetch_posts,
            "fetch_profile": fetch_profile,
        }


async def run_pipeline(
    *,
    config_path: str = "config/config.yaml",
    company_name: Optional[str] = None,
    city: Optional[str] = None,
    fetch_posts: bool = True,
    fetch_profile: bool = True,
) -> Dict[str, Any]:
    """Instantiate the pipeline, load plugins, and run with prepared args."""
    pipeline = DataPipeline(config_path=config_path)
    pipeline.load_plugins()

    arguments = DataPipeline.prepare_arguments(
        company_name=company_name,
        city=city,
        fetch_posts=fetch_posts,
        fetch_profile=fetch_profile,
    )

    return await pipeline.run(arguments)


# ============================================================================
# Manual Testing Code (commented out for production)
# ============================================================================
# Uncomment the code below to test the pipeline manually during development.
# Usage: python -m backend.services.scrapping.pipeline
# ============================================================================

# if __name__ == "__main__":
#     import asyncio
#     async def main():

#         arguments=DataPipeline.prepare_arguments(company_name="artefact",city="paris")

#         """Test the pipeline with the configuration file."""
#         print("=" * 60)
#         print("Testing Data Pipeline")
#         print("=" * 60)

#         # Initialize pipeline
#         pipeline = DataPipeline(config_path="config/config.yaml")

#         # Load plugins
#         print("\nLoading plugins...")
#         pipeline.load_plugins()

#         print(f"Loaded {len(pipeline.plugins)} plugin(s):")
#         for plugin in pipeline.plugins:
#             print(f"   - {plugin.name} ({plugin.__class__.__name__})")

#         # Run pipeline
#         print("\nRunning pipeline...")
#         results = await pipeline.run(arguments)

#         # Display results
#         print("\n" + "=" * 60)
#         print("Results Summary")
#         print("=" * 60)

#         for plugin_name, data in results.items():
#             if isinstance(data, dict) and "error" in data:
#                 print(f"\n {plugin_name}: ERROR")
#                 print(f"   {data['error']}")
#             else:
#                 print(f"\n {plugin_name}: {len(data)} events")
#                 if data:
#                     # Show first event as example
#                     first_event = data[0]
#                     print(f"   Example: {first_event.text[:50]}...")
#                     print(f"   Source: {first_event.source}")
#                     print(f"   URL: {first_event.url}")

#         print("\n" + "=" * 60)
#         print(" Pipeline test completed!")
#         print("=" * 60)

#     # Run the async main function
#     asyncio.run(main())
