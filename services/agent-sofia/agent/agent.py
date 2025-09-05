import asyncio
import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from typing_extensions import override

from .tools.states import State
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
    tools=[CustomerDataToolset(), SalesforceToolset(), RepresentativeToolset()],
)    
root_agent = sofia_agent