
import os
import uvicorn
from dotenv import load_dotenv 
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging


load_dotenv()

logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)


AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Get session service URI from environment variables
session_uri = os.getenv("SESSION_SERVICE_URI", None)

# Prepare arguments for get_fast_api_app
app_args = {"agents_dir": AGENT_DIR, "web": True}

# Only include session_service_uri if it's provided
if session_uri:
    app_args["session_service_uri"] = session_uri
else:
    logger.log_text(
        "SESSION_SERVICE_URI not provided. Using in-memory session service instead. "
        "All sessions will be lost when the server restarts.",
        severity="WARNING",
    )


# Create FastAPI app with appropriate arguments
app: FastAPI = get_fast_api_app(**app_args)

app.title = "agente-sofia"

if __name__ == "__main__":
    # Use environment variables for configuration, with sensible defaults.
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8080)))