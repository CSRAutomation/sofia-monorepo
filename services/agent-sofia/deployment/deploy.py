
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from sofia_agent.agent import root_agent
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

PROJECT_ID = "vertex-466215"
LOCATION = "us-central1"
BUCKET = "cloud-ai-platform-a2287b50-7eff-43fd-9b38-9a06bc2db94c"

USE_VERTEXAI = True

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")

flags.DEFINE_bool("list", False, "List all agents.")
flags.DEFINE_bool("create", False, "Creates a new agent.")
flags.DEFINE_bool("delete", False, "Deletes an existing agent.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete"])

def create() -> None:
    """ Function for the create agent. """
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)
    remote_engine = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        description=root_agent.description,
        requirements=[
            # Dependencias principales de ADK y Vertex AI.
            "google-cloud-aiplatform[adk,agent_engines]",
            # Dependencias para las herramientas del agente.
            "httpx",
            "cloudpickle==3.0",
            "google-genai",
            "google-adk",
            "pydantic",
            "dateparser",
        ],
    )
    print(f"Created remote agent: {remote_engine.resource_name}")

def delete(resource_id: str) -> None:
    """ Function for the delete agent. """
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")

def list_agents() -> None:
    """ Function for the list agent. """
    remote_agents = agent_engines.list()
    template = """
    {agent.name} ("{agent.display_name}")
    - Create time: {agent.create_time}
    - Update time: {agent.update_time}    
    """

    remote_agents_string = "\n".join(
        template.format(agent=agent) for agent in remote_agents
    )
    print(f"Remote agents:\n{remote_agents_string}")

def main (argv: list[str]) -> None:
    
    del argv
    load_dotenv()

    project_id = "vertex-466215"

    location = "us-central1"

    bucket = "cloud-ai-platform-a2287b50-7eff-43fd-9b38-9a06bc2db94c"

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

    if not project_id:
        print("Missing required enviroment variable: GOOGLE_CLOUD_PROJECT")
        return
    elif not location:
        print("Missing required enviroment variable: GOOGLE_CLOUD_LOCATION")
        return
    elif not bucket:
        print("Missing required enviroment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    if FLAGS.list:
        list_agents()
    elif FLAGS.create:
        create()
    elif FLAGS.delete:
        if not FLAGS.resource_id:
            print("resource_id is required for delete")
            return
        delete(FLAGS.resource_id)
    else:
        print("Unknown command")

if __name__ == "__main__":
    app.run(main)   
