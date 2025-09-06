import logging
from google.adk.agents import LlmAgent
from .tools.customer import CustomerDataToolset
from .tools.salesforce import SalesforceToolset
from .tools.representative import RepresentativeToolset
from . import prompts


logger = logging.getLogger(__name__)

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