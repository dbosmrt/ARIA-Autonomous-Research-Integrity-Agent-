"""
Claim extractor node - Uses Gemini Flash to extract testable scientific claims.
"""

import json
import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from Agent.llm import get_gemini_flash
from Agent.state import ReprCheckState, AuditEntry
from Agent.prompts.claim_extraction import(
    CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_HUMAN,
)

logger = logging.getLogger(__name__)

def claim_extractor_node(state: ReprCheckState) -> dict:
    logger.info("Extracting claims...")
    start = datetime.utcnow()
    sections= state.get("sections", {})
    metadata= state.get("metadata",{})

    prompt = CLAIM_EXTRACTION_HUMAN.format(
        title=metadata.get("title", "Unknown"),
        abstract= sections.get("abstract", "Not available"),
        methods=sections.get("methods", "Not available"),
        results=sections.get("results", "Not available"),
        discussion=sections.get("discussion", "Not available"),
    )

    llm = get_gemini_flash()
    response=llm.invoke([
        SystemMessage(content=CLAIM_EXTRACTION_SYSTEM),
        HumanMessage(content=prompt),
    ])

    claims = _parse_claims(response.content)
    elapsed = (datetime.utcnow() - start).total_seconds()*1000
    logger.info(f"Extracted {len(claims)} claims")
    return {
        "claims": claims,
        "audit_trail": [
            AuditEntry(
                agent="claim_extractor",
                action="extracted_claims",
                details=f"Extracted {len(claims)} testable claims",
                latency_ms=elapsed,
            ).model_dump()
        ],
    }

def _parse_claims(response_text: str) -> list[dict]:
    try:
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        claims = json.loads(text)
        if isinstance(claims,list):
            return claims 
        if isinstance(claims,dict) and "claims" in claims:
            return claims["claims"]
    except (json.JSONDecodeError, IndexError):
        pass

    logger.warning("Could not parse claims as JSON, creating fallback claim")
    return [{
        "claim_id": "C1",
        "claim_text": response_text[:500],
        "claim_type": "empirical",
        "section_source": "unknown",
        "evidence_strength": "inferred",
        "supporting_text": "",
    }]
