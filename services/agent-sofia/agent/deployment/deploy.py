import os
import sys
import vertexai

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sofia_agent.agent import root_agent
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

def create () -> None:
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)
    remote_agent = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        description=root_agent.description,
        requirements=[
            "google-adk",
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-genai",
            "scann",
        ],
    )
    print(f"Deployed agent with name: {remote_agent.display_name}, id: {remote_agent.name}")
    print(f"Resource Name: {remote_agent.resource_name}")

def main(argv: list[str]) -> None:
    del argv  # Unused.

    project_id = "vertex-466215"
    location = "us-central1"
    bucket = "cloud-ai-platform-a2287b50-7eff-43fd-9b38-9a06bc2db94c"

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )
    create()
    print(f"Deployment finished!")
if __name__ == "__main__":
    main(sys.argv)