"""
General-purpose verification tools for the Tool Calling Agent.
These check structural consistency across agent outputs — 
sample size mismatches, missing mandatory fields, etc.
"""

from langchain.tools import tool
from typing import Any
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("verification_tools")


@tool
def cross_reference_claims(
    claims_data: list[dict],
    statistical_claims_data: list[dict],
) -> dict:
    """Cross-reference extracted claims against statistical claims to find
    inconsistencies like mismatched sample sizes or missing statistical backing.

    Args:
        claims_data: List of claim dicts from claim extractor (each has claim_id, claim_text, numerical_values)
        statistical_claims_data: List of statistical claim dicts from statistics agent (each has claim_id, stated_sample_size_n, test_type)
    """
    issues = []
    
    # Build lookup by claim_id
    stat_lookup = {}
    for sc in statistical_claims_data:
        cid = sc.get("claim_id", "")
        if cid:
            stat_lookup[cid] = sc

    claims_with_stats = 0
    claims_without_stats = 0

    for claim in claims_data:
        cid = claim.get("claim_id", "")
        claim_text = claim.get("claim_text", "")[:80]

        if cid in stat_lookup:
            claims_with_stats += 1
            sc = stat_lookup[cid]

            # Check sample size consistency
            numerical_values = claim.get("numerical_values", [])
            stat_n = sc.get("stated_sample_size_n")

            # Check if claim mentions controls but stats don't have test
            controls = claim.get("controls_present", False)
            test_type = sc.get("test_type")
            if controls and not test_type:
                issues.append({
                    "claim_id": cid,
                    "issue": "Claim mentions controls but no statistical test was reported",
                    "severity": "medium",
                })
        else:
            claims_without_stats += 1
            # Only flag experimental/empirical claims missing stats
            ctype = claim.get("claim_type", "")
            if ctype in ("experimental", "empirical"):
                issues.append({
                    "claim_id": cid,
                    "issue": f"Experimental claim has no matching statistical claim: '{claim_text}...'",
                    "severity": "high",
                })

    result = {
        "total_claims": len(claims_data),
        "claims_with_statistical_backing": claims_with_stats,
        "claims_without_statistical_backing": claims_without_stats,
        "issues_found": len(issues),
        "issues": issues,
        "flag": "CLAIMS WITHOUT STATISTICAL BACKING" if claims_without_stats > 0 else None,
    }
    logger.info(f"Cross-reference: {claims_with_stats}/{len(claims_data)} claims have stats, {len(issues)} issues found")
    return result


@tool
def flag_missing_details(
    data: list[dict],
    required_fields: list[str],
    data_source: str = "unknown",
) -> dict:
    """Check a list of structured records for missing mandatory fields.
    Returns a summary of which records are missing which fields.

    Args:
        data: List of dicts to check (e.g. claim objects or statistical claim objects)
        required_fields: List of field names that should be non-null and non-empty
        data_source: Name of the agent/source that produced this data (for logging)
    """
    if not data:
        return {"error": "No data provided", "complete": True, "missing_count": 0}

    missing_records = []
    total_missing = 0

    for i, record in enumerate(data):
        record_id = record.get("claim_id", f"record_{i}")
        missing_fields = []

        for field in required_fields:
            value = record.get(field)
            if value is None or value == "" or value == []:
                missing_fields.append(field)

        if missing_fields:
            total_missing += 1
            missing_records.append({
                "record_id": record_id,
                "missing_fields": missing_fields,
            })

    all_complete = total_missing == 0

    result = {
        "data_source": data_source,
        "total_records": len(data),
        "complete_records": len(data) - total_missing,
        "incomplete_records": total_missing,
        "missing_details": missing_records[:20],  # cap output size
        "all_complete": all_complete,
        "flag": f"MISSING DETAILS IN {data_source.upper()}" if not all_complete else None,
    }
    logger.info(f"Missing details check ({data_source}): {total_missing}/{len(data)} records incomplete")
    return result
