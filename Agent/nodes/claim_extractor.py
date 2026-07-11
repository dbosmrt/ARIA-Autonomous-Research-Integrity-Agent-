"""
Claim extractor node - Uses Gemini Flash to extract testable scientific claims.
"""

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from Agent.model import get_nemotron3super
from Agent.state import ReprCheckState, ExtractionResult
from Agent.prompts.claim_extraction import(
    CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_HUMAN,
)
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("claim_extractor")

def claim_extractor_node(state: ReprCheckState) -> dict:
    start = datetime.now(timezone.utc)
    logger.info("Extracting claims...")
    
    full_text = state.get("raw_text", "")
    if not full_text:
        logger.error("raw_text is empty. Make Sure the ingestion Node is running...")
        return {"claims": [], "paper_meta":{}, "audit_trial": []}
    
    llm = get_nemotron3super().with_structured_output(ExtractionResult)
    response = llm.invoke([
        SystemMessage(content=CLAIM_EXTRACTION_SYSTEM),
        HumanMessage(content=CLAIM_EXTRACTION_HUMAN),
        HumanMessage(content=f"Here is the paper to analyze:\n\n{full_text}"),
    ])
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()*1000
    logger.info(f"Claim extraction completed in {elapsed:.2f} ms") 
    
    if isinstance(response, dict):
        return response
    else:
        return {
        "claims": response.claims,
        "paper_meta": {
            "research_paradigm": response.research_paradigm,
            "subdiscipline": response.subdiscipline,
            "paper_section": response.paper_section,
        },
        "extraction_result": response.model_dump(),
    }
