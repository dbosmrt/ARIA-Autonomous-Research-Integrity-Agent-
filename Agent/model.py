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
from langchain_nvidia_ai_endpoints import ChatNVIDIA 

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

def _get_google_api_key() -> str:

    key = os.getenv("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Add it to .env or set as environment variable."
        )
    return key

def _get_nvidia_api_key() -> str:

    key = os.getenv("NVIDIA_NIM_KEY", "")
    if not key:
        raise ValueError(
            "NVIDIA_API_KEY is not set. Add it to .env or set as environment variable."
        )
    return key


@lru_cache
def get_gemini_pro() -> ChatGoogleGenerativeAI:

    return ChatGoogleGenerativeAI(
        model = "gemini-2.5-pro",
        google_api_key = _get_google_api_key(),
        temperature=0.2,
        max_output_tokens=8192,
    )

@lru_cache()
def get_gemini_flash() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=_get_google_api_key(),
        temperature=0.1,
        max_output_tokens=100000,
    )



def get_nemotron3super() -> ChatNVIDIA:
    return ChatNVIDIA(
        model="nvidia/llama-3.3-nemotron-super-49b-v1",
        api_key=_get_nvidia_api_key(),
        temperature=0.6,
        top_p=0.95,
        max_tokens=100000,
    )
