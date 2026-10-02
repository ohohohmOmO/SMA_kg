"""Validate actual exported fusion judgments against the fixed review queue."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.evaluation.audit_fyp_inputs import load_jsonl
from src.evaluation.fyp_dataset import sha256
from src.evaluation.summarize_gold_review import wilson_interval


def summarize(queue, submitted):
    expected, seen = {r["review_id"]: r for r in queue}, set()
    counts = {stage: Counter() for stage in ("dictionary", "semantic")}
    for row in submitted:
        rid = row.get("review_id")
        if rid not in expected or rid in seen:
            raise ValueError("Unknown/duplicate fusion review ID")
        seen.add(rid)
        original = expected[rid]
        for field in ("entity_type", "raw_name", "dictionary_name", "aligned_name"):
            if row.get(field) != original[field]:
                raise ValueError(f"Protected mapping differs: {rid}: {field}")
        if not row.get("reviewer_id") or not row.get("review_date"):
            raise ValueError("Actual reviewer/date required")
        for stage, before, after in (("dictionary", "raw_name", "dictionary_name"),
                                     ("semantic", "dictionary_name", "aligned_name")):
            judgment = row.get(stage + "_judgment")
            allowed = {"not_changed"} if original[before] == original[after] else {"same", "different", "unclear"}
            if judgment not in allowed:
                raise ValueError(f"Invalid {stage} judgment in {rid}")
            if judgment in {"different", "unclear"} and not str(row.get("notes", "")).strip():
                raise ValueError("Different/unclear judgment requires rationale")
            counts[stage][judgment] += 1
    complete = len(seen) == len(queue)
    metrics = {}
    for stage, values in counts.items():
        changed = values["same"] + values["different"] + values["unclear"]
        resolved = values["same"] + values["different"]
        metrics[stage] = {"counts": dict(values), "changed_units_reviewed": changed,
            "correct_among_resolved": values["same"] / resolved if complete and resolved else None,
            "wilson_95": wilson_interval(values["same"], resolved) if complete else None,
            "unknown_fraction_changed": values["unclear"] / changed if complete and changed else None}
    return {"completed": complete, "reviewed": len(seen), "required": len(queue), "stages": metrics,
            "limits": "Random changed-mapping units, n=30; stage subsets and shared canonical entities limit precision. Not fused-edge accuracy."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    queue_path, output = Path(args.queue), Path(args.output)
    queue, errors = load_jsonl(queue_path)
    exported = json.loads(Path(args.reviews).read_text(encoding="utf-8-sig"))
    if errors or exported.get("schema") != "sma_fusion_review_v1" or exported.get("fusion_queue_sha256") != sha256(queue_path):
        raise ValueError("Review export does not match the fixed queue")
    result = summarize(queue, exported["reviews"])
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
