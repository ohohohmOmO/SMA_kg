"""Validate human review entries and report progress without API/model scoring."""

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from src.evaluation.audit_fyp_inputs import DEFAULT_CANDIDATES, DEFAULT_WORKBOOK, REPO_ROOT, load_jsonl, read_annotation_workbook
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.evaluation.audit_fyp_inputs import DEFAULT_CANDIDATES, DEFAULT_WORKBOOK, REPO_ROOT, load_jsonl, read_annotation_workbook

LABELS = {"2", "1", "0", "U"}
CHECKS = ("entity_1_correct", "entity_2_correct", "relation_correct", "direction_correct", "evidence_span_correct")


def text(value):
    return "" if value is None else str(value).strip()


def wilson_interval(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def summarize_reviews(rows):
    issues, final_rows, pairs = [], [], []
    for row in rows:
        cid = row.get("candidate_id", "")
        label = text(row.get("support_label"))
        status = text(row.get("review_status"))
        second = text(row.get("second_support_label"))
        adjudicated = text(row.get("adjudicated_label"))
        required = row.get("requires_second_review") == "yes"
        for field in ("support_label", "second_support_label", "adjudicated_label"):
            value = text(row.get(field))
            if value and value not in LABELS:
                issues.append({"candidate_id": cid, "error": f"invalid {field}: {value}"})
        if status not in {"pending_review", "completed", "needs_adjudication", "excluded"}:
            issues.append({"candidate_id": cid, "error": "invalid review_status"})
        if status == "excluded":
            issues.append({"candidate_id": cid, "error": "exclusion needs an explicit sampling/denominator decision; do not silently remove rows"})
        if label in LABELS:
            required_fields = ("reviewer_id", "review_date", "error_type", *CHECKS)
            missing = [field for field in required_fields if not text(row.get(field))]
            if missing:
                issues.append({"candidate_id": cid, "error": "incomplete primary review", "fields": missing})
            for field in CHECKS:
                if text(row.get(field)) not in {"yes", "no", "unclear"}:
                    issues.append({"candidate_id": cid, "error": f"invalid {field}"})
            if label == "2" and any(text(row.get(field)) != "yes" for field in CHECKS[:4]):
                issues.append({"candidate_id": cid, "error": "direct support conflicts with entity/relation/direction checks"})
            if (label != "2" or text(row.get("evidence_span_correct")) != "yes") and not text(row.get("review_notes")):
                issues.append({"candidate_id": cid, "error": "uncertain/incorrect or inadequate evidence needs review_notes"})
        elif status == "completed":
            issues.append({"candidate_id": cid, "error": "completed row has no valid primary label"})
        valid_second = second in LABELS and all(text(row.get(f)) for f in ("second_reviewer_id", "second_review_date"))
        if second:
            if not valid_second or text(row.get("second_reviewer_id")) == text(row.get("reviewer_id")):
                issues.append({"candidate_id": cid, "error": "second review requires a different reviewer, date, and valid label"})
                valid_second = False
        if required and label in LABELS and valid_second:
            pairs.append((label, second))
        if adjudicated and not text(row.get("adjudication_notes")):
            issues.append({"candidate_id": cid, "error": "adjudication requires reasoning and reviewer/date in notes"})
        conflict = valid_second and label in LABELS and label != second
        unresolved = (required and not valid_second) or (conflict and adjudicated not in LABELS)
        if status == "completed" and label in LABELS and not unresolved:
            final_rows.append({**row, "final_label": adjudicated if adjudicated in LABELS else label})

    groups = {}
    for group in ("primary_random", "challenge"):
        original = [r for r in rows if r.get("sample_group") == group]
        complete = [r for r in final_rows if r.get("sample_group") == group]
        counts = Counter(r["final_label"] for r in complete)
        ready = bool(original) and len(complete) == len(original) and not issues
        resolved = sum(counts[k] for k in ("0", "1", "2"))
        metrics = None
        if ready:
            metrics = {"strict_support_rate_among_resolved": counts["2"] / resolved if resolved else None,
                       "lenient_support_rate_among_resolved": (counts["1"] + counts["2"]) / resolved if resolved else None,
                       "resolved_denominator": resolved, "unknown_count": counts["U"],
                       "unknown_fraction_all_samples": counts["U"] / len(original),
                       "strict_confirmed_fraction_all_samples": counts["2"] / len(original),
                       "strict_support_bounds_if_unknowns_resolve": [counts["2"] / len(original),
                                                                     (counts["2"] + counts["U"]) / len(original)]}
            if group == "primary_random":
                metrics["wilson_95_among_resolved"] = wilson_interval(counts["2"], resolved)
                metrics["interval_note"] = "Approximate independence-based interval; repeated PMIDs may require clustered uncertainty analysis."
        groups[group] = {"sample_count": len(original), "final_review_count": len(complete),
                         "final_label_counts": dict(counts), "ready_for_report": ready, "metrics": metrics}
    agreement = {"independent_review_pairs_entered": len(pairs), "raw_agreement": None, "cohen_kappa_nominal": None}
    if pairs:
        left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
        observed = sum(a == b for a, b in pairs) / len(pairs)
        expected = sum(left[k] * right[k] for k in LABELS) / len(pairs) ** 2
        agreement.update(raw_agreement=observed, cohen_kappa_nominal=(observed - expected) / (1 - expected) if expected < 1 else None)
    return {"groups": groups, "agreement_before_adjudication": agreement, "validation_issues": issues,
            "limits": ["No API calls or invented labels; workbook is read-only.",
                       "No population quality rates for incomplete groups.",
                       "Agreement is based on entered labels; reviewer independence must be documented.",
                       "Support rate does not measure recall, fused-edge correctness or answer quality."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", default=DEFAULT_WORKBOOK)
    parser.add_argument("--candidates-file", default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", required=True, help="New JSON output file; refuses overwrite.")
    args = parser.parse_args()
    rows = read_annotation_workbook(REPO_ROOT / args.workbook)
    candidates, parse_errors = load_jsonl(REPO_ROOT / args.candidates_file)
    expected = {r["candidate_id"]: r for r in candidates}
    actual = [r.get("candidate_id") for r in rows]
    if parse_errors or len(expected) != len(candidates) or len(set(actual)) != len(actual) or set(actual) != set(expected):
        raise ValueError("Candidate identities do not match the fixed sample; run the input audit.")
    protected = ("sample_group", "requires_second_review", "source_pmid", "title", "abstract", "entity_1_name",
                 "entity_1_type", "relation", "entity_2_name", "entity_2_type", "evidence_text")
    if any(str(r.get(f, "")) != str(expected[r["candidate_id"]].get(f, "")) for r in rows for f in protected):
        raise ValueError("Protected sample inputs changed; restore them from the fixed candidate source.")
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), **summarize_reviews(rows)}
    out = (REPO_ROOT / args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["validation_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
