"""Takes document in several format and parses them into LLM ingestable format.
-Currently for the demo purpose I am just gonna make ingestor for .pdf files.
-Will add other features later.

Ingestion node — loads PDF or Markdown into raw_text in state.
"""

import logging
from abc import ABC, abstractmethod
from Agent.state import ReprCheckState
from Agent.Tools.ingestion_tool import DoclingIngestor, MarkDownLoader
from datetime import datetime, timezone 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

#node 
def ingestion_node(state: ReprCheckState) -> dict:
    """
    LangGraph node. Reads file_path from state, loads it, returns raw_text.
    Automatically picks PDF or Markdown loader based on file extension.
    """
    start = datetime.now(timezone.utc)
    file_path = state.get("file_path", "")

    if not file_path:
        logger.error("No file_path in state")
        return {"raw_text": ""}

    if file_path.endswith(".pdf"):
        ingestor = DoclingIngestor()
    elif file_path.endswith(".md"):
        ingestor = MarkDownLoader()
    else:
        logger.error(f"Unsupported file type: {file_path}")
        return {"raw_text": ""}

    raw_text = ingestor.load(file_path)
    elapsed = (datetime.now(timezone.utc)-start).total_seconds()*1000
    logger.info(f"Ingested {len(raw_text)} characters in {elapsed:.1f}ms")
    return {"raw_text": raw_text}