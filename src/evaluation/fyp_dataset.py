"""Read integrated review labels without inventing component judgments."""

import hashlib
import random
from collections import Counter, defaultdict
from pathlib import Path

from src.evaluation.audit_fyp_inputs import DEFAULT_CANDIDATES, load_jsonl, read_annotation_workbook
from src.evaluation.summarize_gold_review import wilson_interval

SPAN_LABELS = {"yes": "yes", "no": "no", "unclear": "unclear",
               "合格": "yes", "不合格": "no", "无法判断": "unclear"}
PROTECTED = ("sample_group", "requires_second_review", "source_pmid", "title", "abstract",
             "entity_1_name", "entity_1_type", "relation", "entity_2_name", "entity_2_type", "evidence_text")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_review_dataset(workbook, candidates_file=DEFAULT_CANDIDATES):
    rows = read_annotation_workbook(Path(workbook))
    candidates, errors = load_jsonl(Path(candidates_file))
    expected = {r["candidate_id"]: r for r in candidates}
    ids = [r.get("candidate_id") for r in rows]
    if errors or len(expected) != len(candidates) or len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError("Workbook candidate identities differ from the frozen sample.")
    issues, warnings = [], []
    for row in rows:
        cid = row["candidate_id"]
        changed = [f for f in PROTECTED if str(row.get(f, "")) != str(expected[cid].get(f, ""))]
        if changed:
            raise ValueError(f"Protected source fields changed: {cid}: {changed}")
        row["support_label"] = str(row.get("support_label", "")).strip()
        span = str(row.get("evidence_span_correct", "")).strip()
        row["span_label"] = SPAN_LABELS.get(span)
        if row["support_label"] not in {"0", "1", "2", "U"}:
            issues.append({"candidate_id": cid, "error": "missing/invalid integrated support label"})
        if row["span_label"] is None:
            issues.append({"candidate_id": cid, "error": "missing/invalid evidence adequacy label"})
        if str(row.get("review_status", "")) != "completed":
            issues.append({"candidate_id": cid, "error": "integrated review not completed"})
        if not row.get("reviewer_id") or not row.get("review_date"):
            issues.append({"candidate_id": cid, "error": "missing review identity/date"})
        if (row["support_label"] != "2" or row["span_label"] != "yes") and not row.get("review_notes"):
            warnings.append({"candidate_id": cid, "warning": "non-passing label lacks rationale"})
    if issues:
        raise ValueError(f"Integrated label validation failed: {issues[:8]}")
    return rows, {"identity_check": "passed", "source_fields_check": "passed",
                  "integrated_labels_check": "passed", "warnings": warnings,
                  "reviewer_ids": dict(Counter(r["reviewer_id"] for r in rows)),
                  "empty_component_fields": {f: sum(not r.get(f) for r in rows) for f in
                     ("entity_1_correct", "entity_2_correct", "relation_correct", "direction_correct")},
                  "independent_second_reviews": sum(bool(r.get("second_reviewer_id") and r.get("second_support_label")) for r in rows)}


def cluster_interval(rows, predicate, replications=2000, seed=20261002):
    groups = defaultdict(list)
    for row in rows:
        groups[row["source_pmid"]].append(row)
    keys, rng = sorted(groups), random.Random(seed)
    if not keys:
        return None
    values = []
    for _ in range(replications):
        sample = [row for key in rng.choices(keys, k=len(keys)) for row in groups[key]]
        values.append(sum(predicate(row) for row in sample) / len(sample))
    values.sort()
    return [values[int(0.025 * (replications - 1))], values[int(0.975 * (replications - 1))]]


def support_statistics(rows):
    counts = Counter(r["support_label"] for r in rows)
    resolved = [r for r in rows if r["support_label"] != "U"]
    n, nr = len(rows), len(resolved)
    result = {"n": n, "unique_pmids": len({r["source_pmid"] for r in rows}),
              "labels": {k: counts[k] for k in ("2", "1", "0", "U")},
              "span_labels": dict(Counter(r["span_label"] for r in rows)),
              "strict_support": counts["2"] / nr if nr else None,
              "lenient_support": (counts["2"] + counts["1"]) / nr if nr else None,
              "unknown_fraction": counts["U"] / n if n else None,
              "strict_all_sample_bounds": [counts["2"] / n, (counts["2"] + counts["U"]) / n] if n else None,
              "wilson_95_strict": wilson_interval(counts["2"], nr),
              "pmid_cluster_bootstrap_95_strict": cluster_interval(resolved, lambda r: r["support_label"] == "2"),
              "bootstrap_seed": 20261002, "bootstrap_replications": 2000,
              "errors": dict(Counter(r.get("error_type") or "not_recorded" for r in rows))}
    return result


def classify_gate(rows, predictions):
    known = [r for r in rows if r["span_label"] in {"yes", "no"}]
    counts = Counter((r["span_label"] == "yes", bool(predictions[r["candidate_id"]])) for r in known)
    tp, fn, fp, tn = counts[True, True], counts[True, False], counts[False, True], counts[False, False]
    retained = [r for r in rows if predictions[r["candidate_id"]]]
    resolved_retained = [r for r in retained if r["support_label"] != "U"]
    return {"n": len(rows), "known_span_labels": len(known), "unknown_span_labels": len(rows) - len(known),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "span_positive_predictive_value": tp / (tp + fp) if tp + fp else None,
            "adequate_span_sensitivity": tp / (tp + fn) if tp + fn else None,
            "inadequate_span_specificity": tn / (tn + fp) if tn + fp else None,
            "retained": len(retained), "retention": len(retained) / len(rows) if rows else None,
            "strict_support_among_retained": sum(r["support_label"] == "2" for r in resolved_retained) / len(resolved_retained) if resolved_retained else None,
            "strict_supported_candidates_retained": sum(r["support_label"] == "2" for r in retained),
            "strict_supported_candidates_total": sum(r["support_label"] == "2" for r in rows),
            "unknown_support_retained": sum(r["support_label"] == "U" for r in retained)}


def candidate_record(row):
    return {"source_pmid": row["source_pmid"], "evidence_text": row["evidence_text"],
            "relation": row["relation"],
            "entity_1": {"name": row["entity_1_name"], "type": row["entity_1_type"]},
            "entity_2": {"name": row["entity_2_name"], "type": row["entity_2_type"]}}


def pmid_split(rows):
    # Development contains the first four examples already inspected. No
    # threshold fitting is performed. Assignment is shared across both groups.
    inspected = {r["source_pmid"] for r in rows if r["candidate_id"] in
                 {f"SMA-RE-{i:04d}" for i in range(1, 5)}}
    return {r["candidate_id"]: ("development" if r["source_pmid"] in inspected or
            int(hashlib.sha256(("20261002:" + r["source_pmid"]).encode()).hexdigest()[:8], 16) % 10 < 3
            else "test") for r in rows}
