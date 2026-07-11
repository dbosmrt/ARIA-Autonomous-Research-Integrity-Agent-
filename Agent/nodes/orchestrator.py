from Agent.model import get_nemotron3super
from Agent.state import ReprCheckState, ClassificationResult
from Agent.logging_config import setup_logging, get_agent_logger
from Agent.prompts.orchestration_prompt import (
    ORCHESTRATION_SYSTEM, ORCHESTRATION_HUMAN,
) 
from datetime import datetime, timezone 
from langchain_core.messages import HumanMessage, SystemMessage 

setup_logging()
logger = get_agent_logger("orchestrator")

def orchestrator_node(state: ReprCheckState) -> dict:
    start = datetime.now(timezone.utc)
    logger.info("Orchestrating the research integrity check...")

    # Default values
    paper = state.get("raw_text", " ")
    claims = state.get("claims", "")

    if not claims or paper:
        logger.error("No claims or paper found in the state.")
        return {"paper_type": "", "agents_to_route": [], "analysis_scope": "", "routing_reasoning": ""} 

    llm = get_nemotron3super().with_structured_output(ClassificationResult)
    response = llm.invoke(
        [
            SystemMessage(content=ORCHESTRATION_SYSTEM),
            HumanMessage(content=ORCHESTRATION_HUMAN), 
            HumanMessage(content=f"\n\nPaper: {paper}\n\nClaims: {claims}")
        ]
    )
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()*1000
    logger.info(f"Orchestration completed in {elapsed:.2f} ms")

    if isinstance(response, dict):
        return response
    else:
        return {  
            "paper_type": getattr(response, "paper_type", ""),
            "agents_to_route": getattr(response, "agents_to_route", []),
            "analysis_scope": getattr(response, "analysis_scope", ""),
            "routing_reasoning": getattr(response, "routing_reasoning", ""),
        } 