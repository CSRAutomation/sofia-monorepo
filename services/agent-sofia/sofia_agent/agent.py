import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import vertexai
import google.auth
from google.cloud import logging as google_cloud_logging
from google.adk.agents import LlmAgent
from .tools.customer import CustomerDataToolset
from .tools.salesforce import SalesforceToolset
from .tools.representative import RepresentativeToolset
from . import prompts

root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Use default project from credentials if not in .env
_, project_id = google.auth.default()
#Google cloud and Vertex AI configuration
PROJECT_ID = os.environ.setdefault("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.setdefault("GOOGLE_CLOUD_LOCATION")
GENAI_USE= os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI")


logging_client = google_cloud_logging.Client()
logger = logging_client.logger("sofia_agentt")

NAME = "Sofia"
MODEL = "gemini-2.0-flash"
DESCRIPTION = "Sofia es una agente de servicio al cliente encargado de crear operaciones especificas en coordinacion con la plataformas Salesforce."


sofia_agent = LlmAgent(
    name=NAME,
    model=MODEL,
    description=DESCRIPTION,
    instruction=prompts.AGENT_CUSTOMER_SERVICE_PROMPT,
    tools=[
        CustomerDataToolset(),
        SalesforceToolset(),
        RepresentativeToolset(),
    ],
)    
root_agent = sofia_agent