"""
test_pipeline.py
Tests ingestion + claim extraction end to end.

Usage:
    python claim_extractor_test.py path/to/paper.pdf
    python claim_extractor_test.py path/to/paper.md
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Agent.nodes.ingestion import ingestion_node
from Agent.nodes.claim_extractor import claim_extractor_node

def run(file_path: str):
    state = {"file_path": file_path}

    # Step 1: Ingestion
    print("\n=== INGESTION ===")
    state.update(ingestion_node(state))
    print(f"Characters loaded: {len(state.get('raw_text', ''))}")

    # Step 2: Claim Extraction
    print("\n=== CLAIM EXTRACTION ===")
    state.update(claim_extractor_node(state))

    claims = state.get("claims", [])
    paper_meta = state.get("paper_meta", {})
    extraction_result = state.get("extraction_result", {})

    print(f"\nPaper Meta:")
    print(f"  paradigm    : {paper_meta.get('research_paradigm')}")
    print(f"  subdiscipline: {paper_meta.get('subdiscipline')}")
    print(f"  section     : {paper_meta.get('paper_section')}")

    print(f"\nTotal claims: {len(claims)}")
    print("="*60)
    for i, claim in enumerate(claims, 1):
        c = claim if isinstance(claim, dict) else claim.model_dump()
        print(f"[{i}] {c.get('claim_text', claim)}")

    # Save to JSON
    output_path = file_path.replace(".md", "_claims_output.json").replace(".pdf", "_claims_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extraction_result, f, indent=2, ensure_ascii=False)
    print(f"\nClaims saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python claim_extractor_test.py path/to/paper.md")
        sys.exit(1)
    run(sys.argv[1])