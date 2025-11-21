import logging
from typing import Any, Dict

import pandas as pd

from backend.services.dataiku.client import DataikuClient
from backend.services.dataiku.transformers import pipeline_results_to_dataframe

logger = logging.getLogger(__name__)


def send_conversation_to_dataiku(conversation: str) -> None:
    """Send conversation pasted by the salesman to dataiku to generate the description."""
    try:
        # 2: create dataframe to send
        conversation_df = pd.DataFrame({"description_p": [conversation], "id": ["gdghvdj"]})

        # 3 Initialize Dataiku client
        client = DataikuClient(
            dss_url="http://172.27.11.206:11200",
            api_key="dkuaps-SSMchnlBMcn5uoAQv5dBtI4b6zWD6hSX",
            project_key="B2B_PROJECT_DATAIKU_MASTER",
            dataset_name="description_p",
        )

        # 4 Connect and push data
        client.connect()
        client.write_dataframe(conversation_df)

        logger.info(
            f"Successfully pushed {len(conversation_df)} rows to Dataiku dataset : description_p."
        )

    except Exception as e:
        logger.exception(f"Failed to send pasted conversation to Dataiku: {e}")
        raise


def send_scraped_data_to_dataiku(pipeline_output: Dict[str, Any]) -> None:
    """Orchestrates sending scraped data to Dataiku:

      1. Loads Dataiku config from config.yaml
      2. Converts scraped data to a normalized DataFrame
      3. Connects to Dataiku
      4. Writes the DataFrame to the target dataset

    Args:
        pipeline_output: dict returned by the scraping pipeline.
    """
    try:
        # 2 Convert scraped pipeline results to DataFrame
        dataframe: pd.DataFrame = pipeline_results_to_dataframe(pipeline_output)
        if dataframe.empty:
            logger.warning("No scraped data to send to Dataiku (empty DataFrame).")
            return

        # 3 Initialize Dataiku client
        client = DataikuClient(
            dss_url="http://172.27.11.206:11200",
            api_key="dkuaps-SSMchnlBMcn5uoAQv5dBtI4b6zWD6hSX",
            project_key="B2B_PROJECT_DATAIKU_MASTER",
            dataset_name="scraped_data",
        )

        # 4 Connect and push data
        client.connect()
        client.write_dataframe(dataframe)

        logger.info(f"Successfully pushed {len(dataframe)} rows to Dataiku dataset : scraped_data.")

    except Exception as e:
        logger.exception(f"Failed to send scraped data to Dataiku: {e}")
        raise
