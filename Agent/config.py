"""
This is a centralized configuration loader 
Loads via Google cloud secret manager, environment variables, .env file.

- Once Loaded caches them too... 
"""

import os
import logging 
from functools import lru_cache
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

def _try_secret_manager(secret_id: str) -> str |None:
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        return None
    
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.debug(f"Secret Manager Unavailable for '{secret_id}' : {e}")
        return None

def get_secret(key: str, secret_id: str | None = None) ->str:

    sm_id = secret_id or key.lower().replace("_", "-")
    value = _try_secret_manager(sm_id)
    if value:
        return value
    
    value = os.getenv(key)
    if value:
        return value
    
    raise ValueError(
        f"Configuration '{key}' not found."
        f"Set in in .env, environment, or Secret Manager (as '{sm_id})."
    )

@lru_cache
class Settings:

    def __init__(self):
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        self.google_api_key: str = get_secret("GOOGLE_API_KEY")
        self.gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
        self.gcp_location: str = os.getenv("GCP_LOCATION", "us-central1")

        self.gitlab_url: str = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.gitlab_token:str = os.getenv("GITLAB_TOKEN", "")

        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

        self.agent_builder_datastore_id: str = os.getenv(
            "AGENT_BUILDER_DATASTORE_ID", ""
        )

        self.rag_corpus_name: str = os.getenv("RAG_CORPUS_NAME", "") #Have to replace it with fetching data form websites.


@property
def is_production(self) -> bool:
    return self.environment == 'production'

@property
def has_gitlab(self) -> bool:
    return bool(self.gitlab_token)

@property
def has_agent_builder(self) -> bool:
    return bool(self.gcp_project_id and self.agent_builder_datastore_id)

@property
def has_tavily(self) -> bool:
    return bool(self.tavily_api_key)


def get_settings() -> Settings:
    return Settings()

