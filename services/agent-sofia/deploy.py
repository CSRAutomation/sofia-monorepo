import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import vertexai
from agent.agent import root_agent
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

def create() -> None:
    # --- Búsqueda y eliminación de agente existente para un despliegue limpio ---
    print(f"Buscando un agente existente con el nombre: {root_agent.name}")
    try:
        existing_agents = agent_engines.list()
        for agent in existing_agents:
            if agent.display_name == root_agent.name:
                print(f"Agente existente encontrado: {agent.resource_name}. Eliminándolo para crear la nueva versión.")
                agent.delete()
                print("Versión anterior del agente eliminada.")
                break
    except Exception as e:
        print(f"Advertencia: No se pudo listar o eliminar agentes existentes. Se procederá a crear uno nuevo. Error: {e}")

    adk_app = AdkApp(agent=root_agent, enable_tracing=True)
    remote_engine = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        description=root_agent.description,
        requirements=[
            "google-adk",
            "google-cloud-aiplatform[adk, agent_engines]",
            "google-genai",
        ],
    )
    print(f"Created remote agent: {remote_engine.resource_name}")

def main (argv: list[str])-> None:
    project_id = "vertex-466215"
    location = "us-central1"
    staging_bucket = "cloud-ai-platform-a2287b50-7eff-43fd-9b38-9a06bc2db94c"
    

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{staging_bucket}",
    )
    create()    

if __name__ == "__main__":
    main(sys.argv)