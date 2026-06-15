from typing import Dict, Any, List

# LangChain / Google Generative AI imports
from langchain_core.messages import HumanMessage, SystemMessage

# Local imports
from Agent.model import get_nemotron3super
from Agent.state import ReprCheckState, Claim, StatisticalExtractionResult
from Agent.prompts.statistics_prompt import (
    STATISTICAL_TEMPLATE_SYSTEM,
    STATISTICAL_TEMPLATE_HUMAN,
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
    import json
    claims_json = json.dumps([claim.dict() for claim in claims], indent=2)

    llm = get_nemotron3super().with_structured_output(StatisticalExtractionResult)

    response: StatisticalExtractionResult = llm.invoke([
        SystemMessage(content=STATISTICAL_EXTRACTION_SYSTEM),
        HumanMessage(content=STATISTICAL_EXTRACTION_HUMAN),
        HumanMessage(content=f"""Extracted Claims: {claims_json}

Raw Text: {raw_text}"""),
    ])

    # Future: Placeholder for statistical tool calling integration
    # At this point, 'response.statistical_claims' and 'response.extracted_raw_values'
    # contain the structured statistical data which can be passed to external tools
    # for further validation or analysis.
    # Example:
    # from Agent.Tools.statistical_validator import validate_statistics
    # validation_results = validate_statistics(response.statistical_claims, response.extracted_raw_values)
    # return_dict["statistical_validation_results"] = validation_results


    logger.info(f"Nemotron extracted {len(response.statistical_claims)} statistical claims.")
    return {
        "statistical_claims": response.statistical_claims,
        "extracted_statistical_values": response.extracted_raw_values,
    }