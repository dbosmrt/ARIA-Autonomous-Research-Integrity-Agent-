"""
claim_extractor_test.py

Runnable test for claim_extractor_node.
Reads a paper already converted to .md and feeds it through the extractor.

Usage:
    python claim_extractor_test.py path/to/paper.md
"""

import json
import logging
import pprint
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Agent.nodes.claim_extractor import claim_extractor_node

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


def run(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    state = {
        "paper_id": file_path.split("/")[-1].replace(".md", ""),
        "raw_text": full_text,
        "sections": {
            "abstract": full_text,   # full text passed as-is, Gemini handles it
            "methods": full_text,
            "results": full_text,
            "discussion": full_text,
        },
        "metadata": {
            "title": file_path.split("/")[-1].replace(".md", "").replace("_", " ").title(),
        },
        "claims": [],
        "paper_meta": {},
        "github_url": "",
        "active_agents": [],
        "paper_type": "",
        "agent_results": [],
        "methodology_verdict": {},
        "stats_verdict": {},
        "code_verdict": {},
        "literature_evidence": [],
        "kg_contradictions": [],
        "wetlab_verdict": {},
        "retry_count": 0,
        "confidence_score": 0.0,
        "final_report": {},
        "audit_trail": [],
    }

    result = claim_extractor_node(state)

    claims = result.get("claims", [])
    paper_meta = result.get("paper_meta", {})

    print("\n" + "="*60)
    print("PAPER META")
    print("="*60)
    pprint.pprint(paper_meta)

    print("\n" + "="*60)
    print(f"EXTRACTED CLAIMS ({len(claims)} total)")
    print("="*60)
    for i, claim in enumerate(claims, 1):
        print(f"\n[{i}] {claim.get('claim_text', '')}")
        print(f"    type       : {claim.get('claim_type')}")
        print(f"    section    : {claim.get('section_source')}")
        print(f"    confidence : {claim.get('confidence')}")
        print(f"    evidence   : {claim.get('evidence_strength')}")
        if claim.get('qrp_flags'):
            print(f"    qrp_flags  : {claim.get('qrp_flags')}")

    print("\n" + "="*60)
    print("AUDIT TRAIL")
    print("="*60)
    for entry in result.get("audit_trail", []):
        print(f"  {entry.get('agent')} | {entry.get('action')} | {entry.get('latency_ms', 0):.0f}ms")

    output_path = file_path.replace(".md", "_claims_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nFull output saved to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python claim_extractor_test.py path/to/paper.md")
        sys.exit(1)
    run(sys.argv[1])