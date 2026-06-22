"""
Reproducibility Evaluator node — the final judge in the pipeline.
Consumes ALL upstream agent outputs (claims, statistics, wet-lab extraction,
tool verification results) and produces a descriptive reproducibility
evaluation with a verdict.

Uses Nemotron for complex reasoning across all evidence dimensions.
"""

from typing import Dict, Any, List
import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from Agent.model import get_nemotron3super
from Agent.state import (
    ReprCheckState,
    Claim,
    StatisticalClaim,
    ReproducibilityEvaluation,
)
from Agent.prompts.wet_lab_prompt import (
    REPRODUCIBILITY_EVAL_SYSTEM,
    REPRODUCIBILITY_EVAL_HUMAN,
)
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("reproducibility_evaluator")


def _collect_evidence(state: ReprCheckState) -> dict:
    """Gather all available upstream evidence from state into a single dict
    that gets serialized as JSON for the evaluator LLM.
    """
    evidence = {}

    # Paper classification
    paper_classification = state.get("paper_classification", {})
    if paper_classification:
        evidence["paper_classification"] = paper_classification

    paper_meta = state.get("paper_meta", {})
    if paper_meta:
        evidence["paper_metadata"] = paper_meta

    # Extracted claims
    claims = state.get("claims", [])
    if claims:
        evidence["extracted_claims"] = [
            c.model_dump() if hasattr(c, "model_dump")
            else (c.dict() if hasattr(c, "dict") else c)
            for c in claims
        ]

    # Statistical claims
    stat_claims = state.get("statistical_claims", [])
    if stat_claims:
        evidence["statistical_claims"] = [
            sc.model_dump() if hasattr(sc, "model_dump")
            else (sc.dict() if hasattr(sc, "dict") else sc)
            for sc in stat_claims
        ]

    # Wet-lab verdict
    wetlab_verdict = state.get("wetlab_verdict", {})
    if wetlab_verdict:
        evidence["wetlab_verdict"] = wetlab_verdict

    # Tool calling agent results (if available)
    tool_summary = state.get("tool_agent_summary", "")
    if tool_summary:
        evidence["tool_verification_summary"] = tool_summary

    tool_results = state.get("tool_execution_results", [])
    if tool_results:
        evidence["tool_execution_results"] = tool_results

    # Methodology verdict (if available from other agents)
    meth_verdict = state.get("methodology_verdict", {})
    if meth_verdict:
        evidence["methodology_verdict"] = meth_verdict

    # Stats verdict (if available)
    stats_verdict = state.get("stats_verdict", {})
    if stats_verdict:
        evidence["stats_verdict"] = stats_verdict

    return evidence


# LangGraph Node Function 

def reproducibility_evaluator_node(state: ReprCheckState) -> Dict[str, Any]:
    """
    LangGraph node that evaluates overall paper reproducibility.
    Consumes all upstream evidence and produces a descriptive
    ReproducibilityEvaluation with a verdict.
    """
    start = datetime.now(timezone.utc)
    logger.info("Reproducibility evaluator started — synthesizing all evidence...")

    # Collect all evidence
    evidence = _collect_evidence(state)

    if not evidence:
        logger.warning("No upstream evidence found in state. Cannot evaluate reproducibility.")
        return {
            "reproducibility_evaluation": {
                "verdict": "insufficient_information",
                "confidence": "low",
                "overall_narrative": "No evidence was available from upstream agents to evaluate reproducibility.",
            },
        }

    # Serialize evidence to JSON
    evidence_json = json.dumps(evidence, indent=2, default=str)

    # Escape braces for .format()
    safe_evidence_json = evidence_json.replace("{", "{{").replace("}", "}}")

    llm = get_nemotron3super().with_structured_output(ReproducibilityEvaluation)

    response: ReproducibilityEvaluation = llm.invoke([
        SystemMessage(content=REPRODUCIBILITY_EVAL_SYSTEM),
        HumanMessage(content=REPRODUCIBILITY_EVAL_HUMAN.format(
            evidence_json=safe_evidence_json,
        )),
    ])

    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    logger.info(
        f"Reproducibility evaluation complete in {elapsed_ms:.1f}ms — "
        f"Verdict: {response.verdict} | Confidence: {response.confidence} | "
        f"Strengths: {len(response.strengths)} | Weaknesses: {len(response.weaknesses)} | "
        f"Critical gaps: {len(response.critical_gaps)}"
    )

    return {
        "reproducibility_evaluation": response.model_dump(),
        "audit_trail": [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "reproducibility_evaluator",
            "action": f"Verdict: {response.verdict} (confidence: {response.confidence})",
            "details": json.dumps({
                "strengths_count": len(response.strengths),
                "weaknesses_count": len(response.weaknesses),
                "critical_gaps_count": len(response.critical_gaps),
            }),
            "latency_ms": elapsed_ms,
        }],
    }
