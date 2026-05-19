"""
This will be Gemini model factory
Will provide pre-configured LLM instances for differenct agent roles:

Uses two models:
    - Gemini 2.5 Pro : Complex reasoning(judge, repro checker)
    - Gemini 2.5 Flash : High throughput (stats, wetlab, extraction)
"""

import os
from functools import lru_cache
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

def _get_api_key() -> str:

    key = os.getenv("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Add it to .env or set as environment variable."
        )
    return key

@lru_cache
def get_gemini_pro() -> ChatGoogleGenerativeAI:

    return ChatGoogleGenerativeAI(
        model = "gemini-2.5-pro",
        google_api_key = _get_api_key(),
        temperature=0.2,
        max_output_tokens=8192,
    )

@lru_cache()
def get_gemini_flash() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=_get_api_key(),
        temperature=0.1,
        max_output_tokens=4096,
    )

def get_model_for_role(role:str) -> ChatGoogleGenerativeAI:
    pro_roles = {"judge", "repro_checker", "gitlab_ci", "report_generator"}
    if role in pro_roles:
        return get_gemini_pro()
    return get_gemini_flash()
