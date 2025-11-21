import time

from dataikuapi import DSSClient


def read_filtered_data():
    """Lire directement les données du dataset,

    avec une pause de 20 secondes après la lecture
    """
    dss_url = "http://172.27.11.206:11200"
    api_key = "dkuaps-SSMchnlBMcn5uoAQv5dBtI4b6zWD6hSX"
    project_key = "B2B_PROJECT_DATAIKU_MASTER"
    dataset_name = "filtered_data"

    time.sleep(20)

    client = DSSClient(dss_url, api_key)
    project = client.get_project(project_key)
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

    time.sleep(10)

    client = DSSClient(dss_url, api_key)
    project = client.get_project(project_key)
    dataset = project.get_dataset(dataset_name)
    core_dataset = dataset.get_as_core_dataset()
    df = core_dataset.get_dataframe()

    return df["conversation"].iloc[0]
