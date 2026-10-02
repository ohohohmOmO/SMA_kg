"""Reproducible offline FYP evaluation; never overwrites canonical artifacts."""

import argparse
import csv
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx

from src.biomedical.evidence_validation import CONFIG, VERSION, validate_evidence
from src.biomedical.schema import normalize_relation
from src.evaluation.audit_fyp_inputs import DEFAULT_CANDIDATES, load_jsonl, locate_evidence, signature
from src.evaluation.fyp_dataset import (candidate_record, classify_gate, pmid_split,
                                      read_review_dataset, sha256, support_statistics)
from src.fusion.dictionary_mapper import load_dictionary, map_entity


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def graph_metrics(records):
    keys = {signature(row) for row in records}
    graph = nx.DiGraph()
    for a, at, _, b, bt in keys:
        graph.add_edge((a, at), (b, bt))
    components = list(nx.weakly_connected_components(graph))
    largest = max(map(len, components), default=0)
    n = len(graph)
    return {"input_records": len(records), "unique_relation_edges": len(keys),
            "typed_nodes": n, "unique_directed_pairs": graph.number_of_edges(),
            "average_total_degree_projected": sum(dict(graph.degree()).values()) / n if n else 0,
            "weak_components": len(components), "largest_component_nodes": largest,
            "outside_largest_component_fraction": (n - largest) / n if n else None,
            "degree_zero_nodes": len(list(nx.isolates(graph))),
            "self_loop_relation_edges": sum(a == b and at == bt for a, at, _, b, bt in keys)}


def validate_stages(raw, mapped, aligned, fused, dictionary):
    if not len(raw) == len(mapped) == len(aligned):
        raise ValueError("Stage counts differ; row-level controls are invalid.")
    mapping_replay_errors, stable_errors = [], []
    changes = {}
    for index, (a, b, c) in enumerate(zip(raw, mapped, aligned)):
        expected = dict(a)
        for key in ("entity_1", "entity_2"):
            expected[key] = map_entity(a[key], dictionary)
        expected["relation"] = normalize_relation(a["relation"]) or a["relation"]
        if signature(expected) != signature(b):
            mapping_replay_errors.append(index)
        for field in ("source_pmid", "evidence_text", "relation"):
            if a.get(field) != b.get(field) or b.get(field) != c.get(field):
                stable_errors.append({"index": index, "field": field})
        for key in ("entity_1", "entity_2"):
            if not a[key]["type"] == b[key]["type"] == c[key]["type"]:
                stable_errors.append({"index": index, "field": key + ".type"})
            names = (a[key]["type"], a[key]["name"], b[key]["name"], c[key]["name"])
            if len(set(names[1:])) > 1:
                unit = changes.setdefault(names, {"entity_type": names[0], "raw_name": names[1],
                    "dictionary_name": names[2], "aligned_name": names[3], "source_pmids": set()})
                unit["source_pmids"].add(str(a["source_pmid"]))
    expected_groups = defaultdict(list)
    for row in aligned:
        expected_groups[signature(row)].append(row)
    seen, provenance_errors = set(), []
    for row in fused:
        key = signature(row)
        group = expected_groups.get(key, [])
        sources = {str(r["source_pmid"]) for r in group}
        evidence = row.get("evidence", {})
        if key in seen or not group or sources != set(map(str, evidence.get("pmid_list", []))) or len(group) != evidence.get("evidence_count"):
            provenance_errors.append(key)
        seen.add(key)
    if set(expected_groups) != seen:
        provenance_errors.append("group keys differ")
    checks = {"dictionary_replay_errors": len(mapping_replay_errors),
              "stable_field_errors": len(stable_errors), "fused_provenance_errors": len(provenance_errors)}
    if any(checks.values()):
        raise ValueError(f"Controlled-comparison prerequisites failed: {checks}")
    return checks, [{**unit, "source_pmids": sorted(unit["source_pmids"])} for _, unit in sorted(changes.items())]


def fusion_comparison(out, datasets, dictionary, abstracts, inputs=None):
    checks, mappings = validate_stages(datasets["raw"], datasets["dictionary"], datasets["semantic"], datasets["fused"], dictionary)
    metrics = {}
    for condition in ("raw", "dictionary", "semantic"):
        condition_dir = out / "fusion" / condition
        condition_dir.mkdir(parents=True)
        input_path = (inputs or {"raw": ROOT / "data/processed/extracted_triples.jsonl",
                      "dictionary": ROOT / "data/interim/mapped_triples.jsonl",
                      "semantic": ROOT / "data/interim/aligned_triples.jsonl"})[condition]
        command = [sys.executable, str(ROOT / "src/fusion/triples_aggregator.py"),
                   "--input-file", str(input_path), "--output-file", str(condition_dir / "fused.jsonl"),
                   "--conflict-file", str(condition_dir / "conflicts.jsonl"),
                   "--rejected-file", str(condition_dir / "rejected.jsonl")]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (condition_dir / "aggregation.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        if run.returncode:
            raise RuntimeError(f"Aggregation failed for {condition}; see its log.")
        fused, errors = load_jsonl(condition_dir / "fused.jsonl")
        rejected, rejects_parse = load_jsonl(condition_dir / "rejected.jsonl")
        conflicts, conflicts_parse = load_jsonl(condition_dir / "conflicts.jsonl")
        if errors or rejects_parse or conflicts_parse or rejected:
            raise ValueError(f"Invalid aggregation output in {condition}")
        source_count = sum(r["evidence"]["evidence_count"] for r in fused)
        if source_count != len(datasets[condition]) or {signature(r) for r in fused} != {signature(r) for r in datasets[condition]}:
            raise ValueError(f"Aggregation count/key preservation failed in {condition}")
        metrics[condition] = {**graph_metrics(datasets[condition]), "conflict_pairs": len(conflicts),
                              "preserved_evidence_records": source_count,
                              "compression_vs_raw_unique_edges": 1 - len(fused) / len({signature(r) for r in datasets["raw"]})}
    checks["semantic_aggregation_reproduces_canonical_bytes"] = sha256(out / "fusion/semantic/fused.jsonl") == sha256((inputs or {}).get("fused", ROOT / "data/processed/fused_triples.jsonl"))
    if not checks["semantic_aggregation_reproduces_canonical_bytes"]:
        raise ValueError("Semantic aggregation did not reproduce the canonical fused snapshot.")
    jsonl(out / "fusion_mapping_changes.jsonl", mappings)
    selected = random.Random(20261002).sample(mappings, min(30, len(mappings)))
    queue = []
    for index, row in enumerate(selected, 1):
        contexts = [{"pmid": pmid, **abstracts[pmid]} for pmid in row["source_pmids"][:2]]
        queue.append({"review_id": f"FUSION-{index:03d}", **row, "source_contexts": contexts,
                      "dictionary_judgment": "", "semantic_judgment": "", "reviewer_id": "", "review_date": "", "notes": ""})
    jsonl(out / "fusion_review_30.jsonl", queue)
    return {"conditions": metrics, "checks": checks, "changed_mapping_units": len(mappings),
            "semantic_mapping_correctness": None,
            "human_review_status": "30 units prepared; no mapping judgments supplied",
            "sampling": "uniform random mapping-change units; seed 20261002; n=30"}, queue


def evidence_comparison(out, rows, raw, abstracts, dictionary):
    evaluations, corpus_counts, corpus_flags = [], Counter(), Counter()
    with (out / "evidence_validation_full.jsonl").open("w", encoding="utf-8") as stream:
        for index, record in enumerate(raw, 1):
            validation = validate_evidence(record, abstracts.get(str(record["source_pmid"])), dictionary)
            corpus_counts[validation["location_status"]] += 1
            corpus_flags.update(validation["flags"])
            stream.write(json.dumps({"raw_record_number": index, "source_pmid": record["source_pmid"],
                                     "triple": {k: record[k] for k in ("entity_1", "relation", "entity_2")},
                                     "validation": validation}, ensure_ascii=False) + "\n")
    split = pmid_split(rows)
    for row in rows:
        record = candidate_record(row)
        validation = validate_evidence(record, abstracts.get(row["source_pmid"]), dictionary)
        literal = locate_evidence(record, abstracts) == "exact"
        evaluations.append({"candidate_id": row["candidate_id"], "sample_group": row["sample_group"],
            "source_pmid": row["source_pmid"], "split": split[row["candidate_id"]],
            "reference_support": row["support_label"], "reference_span": row["span_label"],
            "nonempty": bool(row["evidence_text"].strip()), "literal": literal,
            "traceable": validation["traceable"], "triage_gate": validation["eligible_span"],
            "location_status": validation["location_status"], "flags": "|".join(validation["flags"]),
            "validation": validation})
    jsonl(out / "evidence_candidate_results.jsonl", evaluations)
    write_csv(out / "evidence_candidate_results.csv", [{k: v for k, v in r.items() if k != "validation"} for r in evaluations])
    gates = {gate: {r["candidate_id"]: r[gate] for r in evaluations}
             for gate in ("nonempty", "literal", "traceable", "triage_gate")}
    groups = {}
    for group in ("primary_random", "challenge"):
        for subset in ("all", "development", "test"):
            selected = [r for r in rows if r["sample_group"] == group and (subset == "all" or split[r["candidate_id"]] == subset)]
            groups[f"{group}:{subset}"] = {gate: classify_gate(selected, predictions) for gate, predictions in gates.items()}
    dev_pmids = {r["source_pmid"] for r in evaluations if r["split"] == "development"}
    test_pmids = {r["source_pmid"] for r in evaluations if r["split"] == "test"}
    if dev_pmids & test_pmids:
        raise ValueError("PMID split leakage")
    return {"version": VERSION, "config": CONFIG, "corpus_location_counts": dict(corpus_counts),
            "corpus_review_flags": dict(corpus_flags), "groups": groups,
            "development_pmids": len(dev_pmids), "test_pmids": len(test_pmids),
            "pmid_overlap": 0, "semantic_entailment_implemented": False,
            "evaluation_design": "retrospective fixed-rule internal evaluation; not independent prospective validation"}, evaluations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--mapped-file", default="data/interim/mapped_triples.jsonl")
    parser.add_argument("--aligned-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--fused-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--alignment-policy", default="historical_semantic_threshold_0.88")
    parser.add_argument("--label-provenance", choices=("ai_assisted_unconfirmed", "human_confirmed_all"), default="ai_assisted_unconfirmed")
    parser.add_argument("--provenance-note", default="Human confirmation scope requested; not yet established.")
    args = parser.parse_args()
    workbook = (ROOT / args.workbook).resolve()
    rows, dataset_validation = read_review_dataset(workbook, ROOT / DEFAULT_CANDIDATES)
    inputs = {"workbook": workbook, "candidates": ROOT / DEFAULT_CANDIDATES,
              "abstracts": ROOT / "data/raw/pubmed_sma_abstracts.jsonl",
              "raw": ROOT / "data/processed/extracted_triples.jsonl",
              "dictionary": ROOT / args.mapped_file,
              "semantic": ROOT / args.aligned_file,
              "fused": ROOT / args.fused_file,
              "entity_dictionary": ROOT / "resources/entity_dictionary.json",
              "schema": ROOT / "resources/biomedical_schema.json",
              "evidence_code": ROOT / "src/biomedical/evidence_validation.py",
              "dataset_code": ROOT / "src/evaluation/fyp_dataset.py",
              "runner_code": Path(__file__).resolve(),
              "aggregation_code": ROOT / "src/fusion/triples_aggregator.py"}
    hashes = {name: sha256(path) for name, path in inputs.items()}
    out = (ROOT / args.run_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    dump(out / "run_config.json", vars(args))
    datasets = {}
    for name in ("abstracts", "raw", "dictionary", "semantic", "fused"):
        datasets[name], errors = load_jsonl(inputs[name])
        if errors:
            raise ValueError(f"Invalid JSONL: {name}")
    abstracts = {str(r["pmid"]): r for r in datasets["abstracts"]}
    dictionary = load_dictionary(inputs["entity_dictionary"])
    provenance = {"mode": args.label_provenance, "statement": args.provenance_note,
                  "source_reviewer_ids_preserved": dataset_validation["reviewer_ids"],
                  "label_origin": "human_confirmed_by_user" if args.label_provenance == "human_confirmed_all" else "unconfirmed",
                  "source_metadata_overwritten": False,
                  "independent_human_agreement": None}
    if args.label_provenance == "human_confirmed_all" and args.provenance_note.startswith("Human confirmation scope requested"):
        raise ValueError("Human-confirmed attribution requires the actual user confirmation statement.")
    reference = {group: support_statistics([r for r in rows if r["sample_group"] == group])
                 for group in ("primary_random", "challenge")}
    human = reference if args.label_provenance == "human_confirmed_all" else None
    review_report = {"validation": dataset_validation, "provenance": provenance,
                     "reference_statistics": reference, "human_confirmed_statistics": human,
                     "component_accuracy": None, "extraction_recall": None, "extraction_f1": None}
    dump(out / "review_report.json", review_report)
    jsonl(out / "review_labels_normalized.jsonl", rows)
    fusion, queue = fusion_comparison(out, datasets, dictionary, abstracts, inputs)
    fusion["alignment_policy"] = args.alignment_policy
    dump(out / "fusion_comparison.json", fusion)
    evidence, evaluations = evidence_comparison(out, rows, datasets["raw"], abstracts, dictionary)
    dump(out / "evidence_comparison.json", evidence)
    if any(sha256(path) != hashes[name] for name, path in inputs.items()):
        raise ValueError("Input changed during evaluation")
    manifest = [{"role": name, "path": str(path), "bytes": path.stat().st_size, "sha256": hashes[name]} for name, path in inputs.items()]
    write_csv(out / "manifest.csv", manifest)
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
               "input_mutations": 0, "source_dataset_checks": dataset_validation,
               "fusion_checks": fusion["checks"], "split_pmid_overlap": evidence["pmid_overlap"],
               "human_quality_established": human is not None,
               "pending": (["confirm actual human review scope"] if human is None else []) +
                          ["fusion mapping judgments", "independent second review if agreement is claimed"],
               "limits": ["Traceability and endpoint coverage do not establish semantic entailment.",
                          "Compression does not establish correct fusion.", "No clinical efficacy or novel target claim."]}
    dump(out / "validation_summary.json", summary)
    print(json.dumps({"run_dir": str(out), "review_reference": reference,
                      "fusion": fusion["conditions"], "evidence_test": evidence["groups"]["primary_random:test"],
                      "pending": summary["pending"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
