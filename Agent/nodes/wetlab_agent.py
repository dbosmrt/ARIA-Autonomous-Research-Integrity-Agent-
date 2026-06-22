"""
Wet Lab Agent node — classifies the paper type AND extracts wet-lab
reproducibility signals (reagents, protocols, controls, data transparency)
in a single LLM pass using Nemotron.

Follows the same pattern as statistics_agent.py: reads raw_text + claims
from state, formats them for the LLM, and returns structured output.
"""

from typing import Dict, Any, List
import json

from langchain_core.messages import HumanMessage, SystemMessage

from Agent.model import get_nemotron3super
from Agent.state import (
    ReprCheckState,
    Claim,
    WetlabExtractionResult,
    WetlabVerdict,
)
from Agent.prompts.wet_lab_prompt import (
    WETLAB_AGENT_SYSTEM,
    WETLAB_AGENT_HUMAN,
)
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("wetlab_agent")


#  LangGraph Node Function 

def wetlab_agent_node(state: ReprCheckState) -> Dict[str, Any]:
    """
    LangGraph node that uses Nemotron to:
      1. Classify the paper into a research type
      2. Extract all wet-lab reproducibility signals (reagents, protocols,
         corrntrols, data transparency, etc.)

    Reads raw_text and claims from state, returns paper_classification,
    paper_type, and wetlab_verdict.
    """
    logger.info("Wet-lab agent started — classifying paper and extracting reproducibility signals...")

    raw_text: str = state.get("raw_text", "")
    claims: List[Claim] = state.get("claims", [])

    if not raw_text and not claims:
        logger.error("Both raw_text and claims are empty. Cannot perform wet-lab analysis.")
        return {
            "paper_classification": {},
            "paper_type": "unknown",
            "wetlab_verdict": {},
        }

    # Format claims as JSON for the LLM
    claims_json = json.dumps(
        [claim.model_dump() if hasattr(claim, "model_dump") else claim for claim in claims],
        indent=2,
    )

    # Escape any literal braces in dynamic content so .format() doesn't
    # misinterpret them as format placeholders and raise a KeyError.
    safe_claims_json = claims_json.replace("{", "{{").replace("}", "}}")
    safe_raw_text = raw_text.replace("{", "{{").replace("}", "}}")

    llm = get_nemotron3super().with_structured_output(WetlabExtractionResult)

    response: WetlabExtractionResult = llm.invoke([
        SystemMessage(content=WETLAB_AGENT_SYSTEM),
        HumanMessage(content=WETLAB_AGENT_HUMAN.format(
            extracted_claims=safe_claims_json,
            raw_text=safe_raw_text,
        )),
    ])

    # Build the WetlabVerdict from the extraction result
    verdict = WetlabVerdict(
        classification=response.classification,
        reagents=response.reagents,
        reagents_with_identifiers=sum(
            1 for r in response.reagents if r.identifier
        ),
        reagents_total=len(response.reagents),
        protocols=response.protocols,
        positive_controls_present=response.positive_controls_present,
        negative_controls_present=response.negative_controls_present,
        biological_replicates=response.biological_replicates,
        technical_replicates=response.technical_replicates,
        blinding_reported=response.blinding_reported,
        randomization_reported=response.randomization_reported,
        sample_size_justified=response.sample_size_justified,
        inclusion_exclusion_criteria=response.inclusion_exclusion_criteria,
        raw_data_available=response.raw_data_available,
        code_available=response.code_available,
        protocol_deposited=response.protocol_deposited,
        data_deposited_geo_sra=response.data_deposited_geo_sra,
        accession_numbers=response.accession_numbers,
        methodology_assessment=response.methodology_assessment,
        strengths=response.strengths,
        weaknesses=response.weaknesses,
        flags=response.flags,
        summary=response.summary,
    )

    paper_type = response.classification.primary_type

    logger.info(
        f"Paper classified as: {paper_type} | "
        f"Reagents: {verdict.reagents_total} ({verdict.reagents_with_identifiers} with IDs) | "
        f"Protocols: {len(verdict.protocols)} | "
        f"Flags: {len(verdict.flags)}"
    )

    return {
        "paper_classification": response.classification.model_dump(),
        "paper_type": paper_type,
        "wetlab_verdict": verdict.model_dump(),
    }
