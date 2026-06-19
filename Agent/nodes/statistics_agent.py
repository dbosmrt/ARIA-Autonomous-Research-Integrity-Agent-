from typing import Dict, Any, List
import json
# LangChain / Google Generative AI imports
from langchain_core.messages import HumanMessage, SystemMessage

# Local imports
from Agent.model import get_nemotron3super
from Agent.state import ReprCheckState, Claim, StatisticalExtractionResult
from Agent.prompts.statistics_prompt import (
    STATISTICAL_EXTRACTION_SYSTEM,
    STATISTICAL_EXTRACTION_HUMAN,
)
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("statistics_agent")


#  LangGraph Node Function 
def statistical_claim_extractor_node(state: ReprCheckState) -> Dict[str, Any]:
    """
    LangGraph node that uses Nemotron to extract and structure statistical claims
    and values from the paper's raw text and existing claims.
    """
    logger.info("Extracting statistical claims using Nemotron LLM...")

    raw_text: str = state.get("raw_text", "")
    claims: List[Claim] = state.get("claims", []) # Expecting a list of Claim objects

    if not raw_text and not claims:
        logger.error("Both raw_text and claims are empty. Cannot perform statistical extraction.")
        return {"statistical_claims": [], "extracted_statistical_values": {}}

    # Format claims as JSON for the LLM
    claims_json = json.dumps([claim.dict() for claim in claims], indent=2)


    llm = get_nemotron3super().with_structured_output(StatisticalExtractionResult)

    # Escape any literal braces in dynamic content so .format() doesn't
    # misinterpret them as format placeholders and raise a KeyError.
    safe_claims_json = claims_json.replace("{", "{{").replace("}", "}}")
    safe_raw_text = raw_text.replace("{", "{{").replace("}", "}}")

    response: StatisticalExtractionResult = llm.invoke([
        SystemMessage(content=STATISTICAL_EXTRACTION_SYSTEM),
        HumanMessage(content=STATISTICAL_EXTRACTION_HUMAN.format(
            extracted_claims=safe_claims_json,
            raw_text=safe_raw_text
        )),
    ])


    statistical_claims = response.root
    logger.info(f"Nemotron extracted {len(statistical_claims)} statistical claims.")
    return {
        "statistical_claims": statistical_claims,
        "extracted_statistical_values": {},
    }