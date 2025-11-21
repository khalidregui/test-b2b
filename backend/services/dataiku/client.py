import logging
from typing import Optional

import pandas as pd
from dataikuapi import DSSClient

logger = logging.getLogger(__name__)


class DataikuClient:
    def __init__(self, dss_url: str, api_key: str, project_key: str, dataset_name: str):
        self.dss_url = dss_url
        self.api_key = api_key
        self.project_key = project_key
        self.dataset_name = dataset_name
        self._client: Optional[DSSClient] = None
        self._project = None

    def connect(self) -> None:
        if not all([self.dss_url, self.api_key, self.project_key, self.dataset_name]):
            raise ValueError("Missing Dataiku configuration")
        logger.info("Connecting to Dataiku...")
        self._client = DSSClient(self.dss_url, self.api_key)
        self._project = self._client.get_project(self.project_key)
        logger.info("Connected to Dataiku project %s", self.project_key)

    def write_dataframe(self, dataframe: pd.DataFrame) -> None:
        if self._project is None:
            raise RuntimeError("Not connected to Dataiku. Call connect() first.")
        if dataframe.empty:
            logger.info("No rows to write (empty dataframe).")
            return
        dataset = self._project.get_dataset(self.dataset_name)
        core_dataset = dataset.get_as_core_dataset()
        core_dataset.write_with_schema(dataframe)
        logger.info("Wrote %d rows to Dataiku dataset %s", len(dataframe), self.dataset_name)
