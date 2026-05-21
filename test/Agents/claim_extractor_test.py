"""
test_pipeline.py
Tests ingestion + claim extraction end to end.

Usage:
    python test_pipeline.py path/to/paper.pdf
    python test_pipeline.py path/to/paper.md
"""

import sys
import os

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

    print(f"\nPaper Meta:")
    print(f"  paradigm    : {paper_meta.get('research_paradigm')}")
    print(f"  subdiscipline: {paper_meta.get('subdiscipline')}")
    print(f"  section     : {paper_meta.get('paper_section')}")

    print(f"\nTotal claims: {len(claims)}")
    print("="*60)
    for i, claim in enumerate(claims, 1):
        print(f"[{i}] {claim}")

    # Save to file
    output_path = file_path.replace(".md", "_claims.txt").replace(".pdf", "_claims.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"research_paradigm: {paper_meta.get('research_paradigm')}\n")
        f.write(f"subdiscipline: {paper_meta.get('subdiscipline')}\n")
        f.write(f"paper_section: {paper_meta.get('paper_section')}\n")
        f.write(f"total claims: {len(claims)}\n\n")
        for i, claim in enumerate(claims, 1):
            f.write(f"[{i}] {claim}\n\n")
    print(f"\nClaims saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python claim_extractor_test.py path/to/paper.md")
        sys.exit(1)
    run(sys.argv[1])