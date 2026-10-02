"""Audit current FYP readiness and label provenance; never modifies graph data."""

import argparse
import ast
import csv
import json
import logging
import os
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.evaluation.audit_fyp_inputs import load_jsonl
from src.evaluation.fyp_dataset import sha256


def alignment_diagnostics(mapped, aligned, code_path):
    if len(mapped) != len(aligned):
        raise ValueError("Alignment row counts differ")
    types, changes, pmids, record_ids = defaultdict(set), Counter(), defaultdict(set), defaultdict(set)
    for index, (a, b) in enumerate(zip(mapped, aligned), 1):
        if str(a["source_pmid"]) != str(b["source_pmid"]) or a["evidence_text"] != b["evidence_text"]:
            raise ValueError("Alignment source rows differ")
        for key in ("entity_1", "entity_2"):
            before, after = a[key], b[key]
            types[before["name"]].add(before["type"])
            if before["name"] != after["name"]:
                unit = (before["type"], before["name"], after["name"])
                changes[unit] += 1
                pmids[unit].add(str(a["source_pmid"]))
                record_ids[unit].add(index)
    from src.fusion.semantic_aligner import build_alignment_map, apply_alignment
    synthetic = []
    for _ in range(4):
        synthetic.append({"entity_1": {"type": "Gene", "name": "SHARED"},
                          "entity_2": {"type": "Protein", "name": "shared"}})
    synthetic.append({"entity_1": {"type": "Gene", "name": "shared"},
                      "entity_2": {"type": "Protein", "name": "SHARED"}})
    applied = apply_alignment(synthetic, build_alignment_map(synthetic))
    observed = {"Gene": applied[-1]["entity_1"]["name"], "Protein": applied[-1]["entity_2"]["name"]}
    expected = {"Gene": "SHARED", "Protein": "shared"}
    examples = []
    watched = {"SMN1", "SMN2", "SMA type III", "SMA type II", "SMA type 3", "SMA type 2"}
    for key, count in sorted(changes.items()):
        if key[1] in watched:
            examples.append({"type": key[0], "from": key[1], "to": key[2],
                             "endpoint_occurrences": count, "affected_records": len(record_ids[key]),
                             "unique_pmids": len(pmids[key])})
    return {"input_names_assigned_multiple_types": sum(len(t) > 1 for t in types.values()),
            "observed_mapping_examples": examples,
            "untyped_map_synthetic_reproduction": {"synthetic_only": True,
                "actual_key_expression": "(entity_type, entity_name)", "observed": observed,
                "expected": expected, "type_overwrite_detected": observed != expected},
            "single_linkage_example": {"automatic_semantic_clustering": False,
                "interpretation": "Similarity proposals are review-only; automatic typed identity retains qualifiers."},
            "limits": "Occurrence counts describe observed transformations, not adjudicated fused-edge error rates."}


def live_database_check():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase, READ_ACCESS
    load_dotenv(ROOT / ".env")
    fields = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD")
    if not all(os.getenv(field) for field in fields):
        return {"status": "not_checked_missing_credentials", "database_mutations": 0}
    logging.getLogger("neo4j").setLevel(logging.CRITICAL)
    try:
        with GraphDatabase.driver(os.environ[fields[0]], auth=(os.environ[fields[1]], os.environ[fields[2]]),
                                  connection_timeout=5, max_transaction_retry_time=0) as driver:
            driver.verify_connectivity()
            with driver.session(default_access_mode=READ_ACCESS) as session:
                active = session.run("MATCH (m:SMAGraphMetadata {name:'active'}) RETURN m.graph_version AS v").single()
                if not active:
                    return {"status": "no_active_typed_graph", "database_mutations": 0}
                version = active["v"]
                nodes = session.run("MATCH (n:SMAEntity {graph_version:$v}) RETURN count(n) AS nodes,count(DISTINCT n.entity_key) AS distinct_keys", v=version).single().data()
                relationships = [r.data() for r in session.run("MATCH (:SMAEntity)-[r]->(:SMAEntity) WHERE r.graph_version=$v "
                    "RETURN r.source AS source,count(r) AS relationships,sum(CASE WHEN r.review_status = 'needs_review' THEN 1 ELSE 0 END) AS needs_review ORDER BY source", v=version)]
                missing = session.run("MATCH (:SMAEntity)-[r]->(:SMAEntity) WHERE r.graph_version=$v AND r.source = 'Literature_NLP' RETURN "
                    "sum(CASE WHEN r.evidence_pmids IS NULL OR size(r.evidence_pmids)=0 THEN 1 ELSE 0 END) AS missing_pmid_list", v=version).single().data()
                return {"status": "read_only_live_check_passed", "graph_version": version, "managed_nodes": nodes,
                        "managed_relationships": relationships, "literature_provenance": missing,
                        "database_mutations": 0}
    except Exception as error:
        return {"status": "connection_not_established", "error_class": type(error).__name__, "database_mutations": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--attempt-live-db", action="store_true")
    args = parser.parse_args()
    out = (ROOT / args.run_dir).resolve()
    target = out / "completion_audit.json"
    if target.exists():
        raise FileExistsError("Audit already exists; use a new run directory")
    with (out / "manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        inputs = {r["role"]: r for r in csv.DictReader(stream)}
    if any(sha256(row["path"]) != row["sha256"] for row in inputs.values()):
        raise ValueError("Evaluation inputs or code no longer match this run")
    datasets = {}
    for name in ("dictionary", "semantic"):
        datasets[name], errors = load_jsonl(Path(inputs[name]["path"]))
        if errors:
            raise ValueError("Invalid alignment JSONL")
    review = json.loads((out / "review_report.json").read_text(encoding="utf-8"))
    diagnostics = alignment_diagnostics(datasets["dictionary"], datasets["semantic"], ROOT / "src/fusion/semantic_aligner.py")
    result = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "human_annotation_status": review["provenance"],
              "main_human_support": review["human_confirmed_statistics"]["primary_random"] if review["human_confirmed_statistics"] else None,
              "alignment": diagnostics,
              "database": live_database_check() if args.attempt_live_db else {"status": "not_requested", "database_mutations": 0},
              "overall_status": "typed_identity_repaired; see current quality/database/scope acceptance artifacts",
              "blocking_quality_work": ["independent review of remaining dictionary mappings if a mapping-correctness rate is claimed",
                                        "stronger extraction support on independently evaluated new predictions before claiming adequate full-graph quality"],
              "reporting_work": ["integrate full report and critical literature/methods discussion",
                                 "document failure analysis and the sensitivity/retention trade-off"],
              "not_required_to_claim_current_results": ["re-entering the 400 labels", "invented independent agreement",
                                                        "unmeasured extraction recall/F1", "all conflict pairs adjudicated"],
              "read_only_inputs_verified": True,
              "source_code_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path) for path in
                  (Path(__file__), ROOT / "src/fusion/semantic_aligner.py", ROOT / "src/database/neo4j_importer.py")}}
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(target), "human_annotations_confirmed": review["provenance"]["mode"] == "human_confirmed_all",
                      "type_key_overwrite_detected": diagnostics["untyped_map_synthetic_reproduction"]["type_overwrite_detected"],
                      "database": result["database"], "overall_status": result["overall_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
