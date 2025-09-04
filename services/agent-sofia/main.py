import logging
import os

from google.adk import run
from agent.agent import root_agent

# Configurar logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # La función `run` de ADK inicia el servidor del agente.
    # Utiliza automáticamente la variable de entorno PORT, compatible con Cloud Run.
    logger.info("Iniciando el Agente Sofía...")
    run(root_agent)