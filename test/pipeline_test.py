"""
pipeline_test.py
Tests ingestion + claim extraction + statistics end to end.

Usage:
    python pipeline_test.py path/to/paper.md
    python pipeline_test.py path/to/paper.pdf
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Agent.nodes.ingestion import ingestion_node
from Agent.nodes.claim_extractor import claim_extractor_node
from Agent.nodes.statistics_agent import statistical_claim_extractor_node

def run(file_path: str):
    print(f"\n{'='*60}")
    print(f"Testing ARIA Pipeline on: {file_path}")
    print(f"{'='*60}")

    # Initial state
    state = {"file_path": file_path}

    # Step 1: Ingestion
    print(f"\n{'='*20} STEP 1: INGESTION {'='*20}")
    state.update(ingestion_node(state))
    raw_text = state.get("raw_text", "")
    print(f"✓ Characters loaded: {len(raw_text)}")
    if len(raw_text) > 200:
        print(f"  Preview: {raw_text[:200]}...")
    else:
        print(f"  Text: {raw_text}")

    # Step 2: Claim Extraction
    print(f"\n{'='*20} STEP 2: CLAIM EXTRACTION {'='*20}")
    state.update(claim_extractor_node(state))

    claims = state.get("claims", [])
    paper_meta = state.get("paper_meta", {})
    extraction_result = state.get("extraction_result", {})

    print(f"✓ Paper Meta:")
    print(f    paradigm    : {paper_meta.get('research_paradigm', 'N/A')}")
    print(f    subdiscipline: {paper_meta.get('subdiscipline', 'N/A')}")
    print(f    section     : {paper_meta.get('paper_section', 'N/A')}")

    print(f"✓ Total claims extracted: {len(claims)}")
    print("="*60)
    for i, claim in enumerate(claims, 1):
        # Handle both dict and Claim object
        if hasattr(claim, 'model_dump'):
            c = claim.model_dump()
        elif isinstance(claim, dict):
            c = claim
        else:
            # Fallback - try to access attributes
            c = {
                'claim_id': getattr(claim, 'claim_id', f'claim_{i}'),
                'claim_text': getattr(claim, 'claim_text', str(claim)),
                'claim_type': getattr(claim, 'claim_type', 'unknown'),
                'section_source': getattr(claim, 'section_source', 'unknown'),
            }

        print(f"[{i}] {c.get('claim_text', 'N/A')}")
        print(f      Type: {c.get('claim_type', 'N/A')} | Section: {c.get('section_source', 'N/A')}")

    # Save claims to JSON (like the existing test)
    output_path = file_path.replace(".md", "_claims_output.json").replace(".pdf", "_claims_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extraction_result, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Claims saved to: {output_path}")

    # Step 3: Statistics Extraction
    print(f"\n{'='*20} STEP 3: STATISTICS EXTRACTION {'='*20}")
    state.update(statistical_claim_extractor_node(state))

    statistical_claims = state.get("statistical_claims", [])
    extracted_statistical_values = state.get("extracted_statistical_values", {})

    print(f"✓ Statistical claims extracted: {len(statistical_claims)}")
    print("="*60)
    for i, claim in enumerate(statistical_claims, 1):
        # Handle both dict and StatisticalClaim object
        if hasattr(claim, 'model_dump'):
            c = claim.model_dump()
        elif isinstance(claim, dict):
            c = claim
        else:
            # Fallback - try to access attributes
            c = {
                'claim_id': getattr(claim, 'claim_id', f'claim_{i}'),
                'test_type': getattr(claim, 'test_type', 'N/A'),
                'test_statistic_type': getattr(claim, 'test_statistic_type', 'N/A'),
                'test_statistic_value': getattr(claim, 'test_statistic_value', 'N/A'),
                'p_value': getattr(claim, 'p_value', 'N/A'),
            }

        print(f"[{i}] Claim ID: {c.get('claim_id', 'N/A')}")
        print(f      Test: {c.get('test_type', 'N/A')} ({c.get('test_statistic_type', 'N/A')} = {c.get('test_statistic_value', 'N/A')})")
        print(f      p-value: {c.get('p_value', 'N/A')}")

    if extracted_statistical_values:
        print(f"\n✓ Extracted statistical values:")
        for key, values in extracted_statistical_values.items():
            print(f      {key}: {values}")

    # Save statistics output
    stats_output_path = file_path.replace(".md", "_stats_output.json").replace(".pdf", "_stats_output.json")
    stats_output = {
        "statistical_claims": [c.model_dump() if hasattr(c, 'model_dump') else c for c in statistical_claims],
        "extracted_statistical_values": extracted_statistical_values
    }
    with open(stats_output_path, "w", encoding="utf-8") as f:
        json.dump(stats_output, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Statistics saved to: {stats_output_path}")

    print(f"\n{'='*60}")
    print(f"PIPELINE TEST COMPLETED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"Summary:")
    print(f  - Raw text characters: {len(raw_text)}")
    print(f  - Claims extracted: {len(claims)}")
    print(f  - Statistical claims extracted: {len(statistical_claims)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline_test.py path/to/paper.md")
        print("       python pipeline_test.py path/to/paper.pdf")
        sys.exit(1)
    run(sys.argv[1])