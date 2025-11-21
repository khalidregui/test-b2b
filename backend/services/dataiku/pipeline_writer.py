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


if __name__ == "__main__":
    from datetime import datetime

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
    conversation = """
Subject: RE: SIM Card Activation

Oumar TRAORE <TLOUMAR@hotmail.com>
Wed 5 Nov, 18:57
to TRAORE Adjaratou /OB [OBF], TRAORE Lancina (lassopremier@gmail.com), asalfows@gmail.com, ZAKARIA Karim [OBF]

CAUTION: This email originated outside the company. Do not click on any links or open attachments unless you are expecting them from the sender.
ATTENTION: This email comes from outside the company. Do not click on links or open attachments unless you know the sender.

Good evening Mrs. COMPAORE,

Well received and thank you for your prompt action.

Kind regards,

Oumar

** Please consider the environment before printing this e-mail **

From: adjaratou.traore@orange.com <adjaratou.traore@orange.com>
Sent: Wednesday, November 5, 2025 16:08
To: Oumar TRAORE <TLOUMAR@hotmail.com>
Cc: TRAORE Lancina (lassopremier@gmail.com) <lassopremier@gmail.com>; asalfows@gmail.com; ZAKARIA Karim [OBF] <karim.zakaria@orange.com>
Subject: RE: SIM Card Activation

Hello Mr. TRAORE,

Your request has been processed successfully. Below is the list of numbers:

892260201077788815 22644217005
892260201077788816 22644217006
892260201077788817 22644217007
892260201077788818 22644217008
892260201077788819 22644217009

892260201077788820 22644217010
892260201077788821 22644217011
892260201077788822 22644217012
892260201077788823 22644217013
892260201077788824 22644217014

Kind regards.

Adjaratou TRAORE /OBF/OB
Corporate Account Manager
Mobile: +(226) 76260854

Our Purpose: "At Orange BF, through our digital solutions, we act responsibly to improve the well-being of all."

From: Oumar TRAORE <TLOUMAR@hotmail.com>
Sent: Thursday, October 30, 2025 19:45
To: TRAORE Adjaratou /OB [OBF] <adjaratou.traore@orange.com>
Cc: TRAORE Lancina (lassopremier@gmail.com) <lassopremier@gmail.com>; asalfows@gmail.com; ZAKARIA Karim [OBF] <karim.zakaria@orange.com>
Subject: SIM Card Activation

CAUTION: This email originated outside the company. Do not click on any links or open attachments unless you are expecting them from the sender.
ATTENTION: This email comes from outside the company. Do not click on links or open attachments unless you know the sender.

Good evening Mrs. COMPAORE,

Kindly activate the SIM cards (10 in total) and integrate them into the ANAM account. The numbers will be created and linked to the M2M intense (500MB) plan like the others.

Serial numbers: From 892 260 201 077 788 815 to 892 260 201 077 824

Kind regards,

National Meteorology Agency of Burkina Faso

Oumar TRAORE
Head of Meteorological and IT Equipment Service

4321, Avenue Jean-Baptiste-Ouédraogo
01 BP 576, Ouagadougou 01, Burkina Faso

✉ tloumar@hotmail.com
🌐 www.meteoburkina.bf
📱 +226 76 15 42 35
📲 +226 70 76 16 84 (WhatsApp)

** Please consider the environment before printing this e-mail **

____________________________________________________________________________________________________________
This message and its attachments may contain confidential or privileged information and should not be distributed,
used, or copied without authorization. If you have received this message in error, please notify the sender and delete
it along with the attachments. Since emails can be altered, Orange declines all responsibility if this message has been
modified, changed, or falsified. Thank you.
"""

    send_scraped_data_to_dataiku(pipeline_output)
    send_conversation_to_dataiku(conversation)
