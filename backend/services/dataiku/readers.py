import time

from dataikuapi import DSSClient
from loguru import logger


def read_filtered_data():
    """Lire directement les données du dataset,

    avec une pause de 20 secondes après la lecture
    """
    dss_url = "http://172.27.11.206:11200"
    api_key = "dkuaps-SSMchnlBMcn5uoAQv5dBtI4b6zWD6hSX"
    project_key = "B2B_PROJECT_DATAIKU_MASTER"
    dataset_name = "filtered_data"
    scenario_id = "AUTOUPDATEFILTEREDDATA"
    
    client = DSSClient(dss_url, api_key)
    project = client.get_project(project_key)
    scenario = project.get_scenario(scenario_id)
    
    time.sleep(10)
    scenario_run = scenario.get_last_runs()[0]
    
    while True:
      scenario_run.refresh()
      if scenario_run.running:
        logger.info("Scenario is still running ...")
      else:
        logger.info("Scenario is not running anymore")
        break
      time.sleep(3)

    dataset = project.get_dataset(dataset_name)
    core_dataset = dataset.get_as_core_dataset()

    return core_dataset.get_dataframe()


def read_description():
    """Lire directement les données du dataset,

    avec une pause de 10 secondes après la lecture
    """
    dss_url = "http://172.27.11.206:11200"
    api_key = "dkuaps-SSMchnlBMcn5uoAQv5dBtI4b6zWD6hSX"
    project_key = "B2B_PROJECT_DATAIKU_MASTER"
    dataset_name = "description"
    scenario_id = "AUTOUPDATEDESCRIPTION"
    
    client = DSSClient(dss_url, api_key)
    project = client.get_project(project_key)
    scenario = project.get_scenario(scenario_id)

    time.sleep(5)
    scenario_run = scenario.get_last_runs()[0]
    
    #scenario_run.refresh()
    #while not scenario_run.running:
        #scenario_run.refresh()

    while True:
        scenario_run.refresh()
        if scenario_run.running:
            logger.info("Scenario is still running ...")
        else:
            logger.info("Scenario is not running anymore")
            break
        time.sleep(3)

    dataset = project.get_dataset(dataset_name)
    core_dataset = dataset.get_as_core_dataset()
    df = core_dataset.get_dataframe()

    return df["description"].iloc[0]
