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
    tree = ast.parse(Path(code_path).read_text(encoding="utf-8-sig"))
    functions = [f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name in
                 {"get_canonical_name", "connected_components"}]
    namespace = {"deque": deque}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(code_path), "exec"), namespace)
    main = next(f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == "main")
    assignments = [n for n in ast.walk(main) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                           and t.value.id == "global_alignment_map" for t in n.targets)]
    target = assignments[-1].targets[0]
    lookup = next(n for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and isinstance(n.func.value, ast.Name) and n.func.value.id == "global_alignment_map"
                  and n.func.attr == "get")
    mapping = {}
    freq = {"Shared": 1, "GeneAnchor": 10, "ProteinAnchor": 10}
    for etype, component in (("Gene", ["Shared", "GeneAnchor"]), ("Protein", ["Shared", "ProteinAnchor"])):
        canonical = namespace["get_canonical_name"](component, freq)
        for entity in component:
            key = eval(compile(ast.Expression(target.slice), "<map-key>", "eval"), {},
                       {"entity": entity, "etype": etype})
            mapping[key] = canonical
    observed = {}
    for etype in ("Gene", "Protein"):
        observed[etype] = eval(compile(ast.Expression(lookup), "<map-lookup>", "eval"), {},
                              {"global_alignment_map": mapping, "name": "Shared", "etype": etype,
                               "entity": {"name": "Shared", "type": etype}})
    chain = namespace["connected_components"](["A", "B", "C"],
                                               [[1, .89, .60], [.89, 1, .89], [.60, .89, 1]], .88)
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
                "actual_key_expression": ast.unparse(target.slice), "assignment_line": target.lineno,
                "lookup_line": lookup.lineno, "observed": observed,
                "expected": {"Gene": "GeneAnchor", "Protein": "ProteinAnchor"},
                "type_overwrite_detected": observed != {"Gene": "GeneAnchor", "Protein": "ProteinAnchor"}},
            "single_linkage_example": {"threshold": .88, "a_c_similarity": .60,
                "components": chain, "interpretation": "Connected paths do not ensure every member exceeds the threshold to its canonical representative."},
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
                nodes = session.run("MATCH (n:Entity) WHERE n.kg_sma_managed = true RETURN count(n) AS nodes, "
                                    "sum(CASE WHEN n:Gene AND n:Protein THEN 1 ELSE 0 END) AS gene_and_protein_nodes").single().data()
                relationships = [r.data() for r in session.run("MATCH ()-[r]->() WHERE r.source IN ['Literature_NLP','OpenTargets'] "
                    "RETURN r.source AS source,count(r) AS relationships,sum(CASE WHEN r.review_status = 'needs_review' THEN 1 ELSE 0 END) AS needs_review ORDER BY source")]
                missing = session.run("MATCH ()-[r]->() WHERE r.source = 'Literature_NLP' RETURN "
                    "sum(CASE WHEN r.evidence_pmids IS NULL OR size(r.evidence_pmids)=0 THEN 1 ELSE 0 END) AS missing_pmid_list").single().data()
                return {"status": "read_only_live_check_passed", "managed_nodes": nodes,
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
              "overall_status": "core_prototype_evaluated; final_quality_and_scope_gates_open",
              "blocking_quality_work": ["prevent incompatible entity merges and type-key overwrites",
                                        "validate changed-mapping correctness and rerun controlled fusion",
                                        "define database identity and verify a current read-only snapshot"],
              "reporting_work": ["align preliminary-report promises with actual core scope",
                                 "integrate full report and critical literature/methods discussion",
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
