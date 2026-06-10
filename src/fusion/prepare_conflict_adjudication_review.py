import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evidence.loaders import display_path, load_jsonl, write_json, write_jsonl


HUMAN_REVIEW_DECISIONS = {"real_conflict_needs_human_review", "insufficient_evidence"}
NO_GRAPH_CHANGE_DECISIONS = {"direction_error"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert live conflict adjudications into a human-review promotion proposal."
    )
    parser.add_argument("--adjudications-file", required=True)
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--output-file", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"conflict_adjudication_review_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    output_file = (REPO_ROOT / args.output_file).resolve() if args.output_file else run_dir / "adjudication_review_proposals.jsonl"

    adjudications, bad_lines = load_jsonl(REPO_ROOT / args.adjudications_file)
    if bad_lines:
        write_json(run_dir / "validation_summary.json", {
            "valid": False,
            "bad_adjudication_json_lines": len(bad_lines),
            "canonical_graph_mutated": False,
        })
        return 1

    proposals = [build_review_proposal(record) for record in adjudications]
    write_jsonl(output_file, proposals)
    action_counts = Counter(item["promotion_action"] for item in proposals)
    summary = {
        "valid": True,
        "adjudication_records": len(adjudications),
        "proposal_records": len(proposals),
        "promotion_action_counts": dict(sorted(action_counts.items())),
        "output_file": display_path(output_file),
        "canonical_graph_mutated": False,
        "next_step": "Human reviewer must approve proposals before any canonical graph promotion.",
    }
    write_json(run_dir / "validation_summary.json", summary)
    return 0


def build_review_proposal(record):
    decision = record.get("decision", "")
    retained = list(record.get("retained_relations", []) or [])
    rejected = list(record.get("rejected_relations", []) or [])
    if decision in HUMAN_REVIEW_DECISIONS:
        action = "human_review_required"
    elif decision in NO_GRAPH_CHANGE_DECISIONS:
        action = "no_graph_change"
    elif retained or rejected:
        action = "propose_relation_updates"
    else:
        action = "human_review_required"
    return {
        "conflict_id": record.get("conflict_id", ""),
        "entity_1": record.get("entity_1", {}),
        "entity_2": record.get("entity_2", {}),
        "conflicting_relations": record.get("conflicting_relations", []),
        "decision": decision,
        "promotion_action": action,
        "retain_relations_after_review": retained,
        "reject_relations_after_review": rejected,
        "supporting_pmids": record.get("supporting_pmids", []),
        "confidence": record.get("confidence", 0.0),
        "rationale": record.get("rationale", ""),
        "model": record.get("model", ""),
        "requires_human_approval": True,
        "canonical_graph_mutated": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
