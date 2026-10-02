"""Versioned typed graph import. Historical Entity graphs are never cleared."""
import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from neo4j import GraphDatabase, READ_ACCESS
from src.biomedical.schema import normalize_entity_type, normalize_relation
from src.biomedical.entity_identity import entity_id, authority_ids
from src.evaluation.audit_fyp_inputs import signature
from src.evaluation.fyp_dataset import sha256
from src.extraction.llm_extractor import load_local_env

SAFE_CYPHER_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_label(raw_type):
    label = normalize_entity_type(raw_type) or "Unknown"
    return label if SAFE_CYPHER_TOKEN.fullmatch(label) else "Unknown"


def safe_relationship_type(raw_relation):
    rel = normalize_relation(raw_relation) or "ASSOCIATED_WITH"
    return rel if SAFE_CYPHER_TOKEN.fullmatch(rel) else "ASSOCIATED_WITH"


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def edge_key(version, source, a, relation, b):
    return hashlib.sha256(json.dumps([version, source, a, relation, b], separators=(",", ":")).encode()).hexdigest()


def build_import_records(fused, external, aligned, quality, version):
    if len(aligned) != len(quality):
        raise ValueError("Aligned/quality sidecar counts differ")
    nodes, edges, groups = {}, [], defaultdict(list)
    def node(entity, namespace="literature", source_id=""):
        if safe_label(entity["type"]) == "Unknown" or not str(entity["name"]).strip():
            raise ValueError("Invalid entity identity")
        identity_entity = {"type": entity["type"], "name": source_id or entity["name"]}
        local_id = entity_id(identity_entity, namespace)
        key = version + ":" + local_id
        payload = {"entity_key": key, "entity_id": local_id, "graph_version": version,
                   "name": entity["name"].strip(), "type": entity["type"], "namespace": namespace,
                   "source_id": source_id, **authority_ids(entity)}
        if key in nodes and nodes[key] != payload:
            raise ValueError("Conflicting names for one source identifier")
        nodes[key] = payload
        return key
    for i, (row, q) in enumerate(zip(aligned, quality), 1):
        original = q["original_assertion"]
        if q["raw_record_number"] != i or str(original["source_pmid"]) != str(row["source_pmid"]) or original["evidence_text"] != row["evidence_text"]:
            raise ValueError("Evidence sidecar identity differs")
        groups[signature(row)].append({"raw_record_number": i, "source_pmid": str(original["source_pmid"]),
            "original_entity_1": original["entity_1"], "original_entity_2": original["entity_2"],
            "original_relation": original["relation"], "evidence_text": original["evidence_text"],
            "context_sentences": q["quality"]["context_sentences"], "review_flags": q["quality"]["flags"],
            "semantic_support": "not_evaluated"})
    seen = set()
    for row in fused:
        sig = signature(row); records = groups.get(sig, [])
        pmids = sorted({r["source_pmid"] for r in records})
        if sig in seen or not records or len(records) != row["evidence"]["evidence_count"] or set(pmids) != set(map(str, row["evidence"]["pmid_list"])):
            raise ValueError("Incomplete or duplicate fused evidence join")
        seen.add(sig)
        a, b = node(row["entity_1"]), node(row["entity_2"])
        relation = row["relation"]
        if normalize_relation(relation) != relation: raise ValueError("Noncanonical relation")
        pending = any(r["review_flags"] for r in records)
        edges.append({"a": a, "b": b, "relation": relation, "props": {
            "edge_key": edge_key(version, "Literature_NLP", a, relation, b), "graph_version": version,
            "source": "Literature_NLP", "confidence": row.get("computed_confidence"),
            "confidence_kind": "heuristic_not_accuracy", "evidence_pmids": pmids,
            "evidence_count": len(records), "assertion_records_json": json.dumps(records, ensure_ascii=False),
            "potential_conflict": row.get("review_status") == "needs_review",
            "review_status": "needs_review" if pending or row.get("review_status") == "needs_review" else "screened_candidate",
            "semantic_support": "not_verified"}})
    if seen != set(groups): raise ValueError("Some evidence groups are missing")
    for row in external:
        a = node({"name": row["gene_symbol"], "type": "Gene"}, "opentargets", row["target_id"])
        b = node({"name": row["disease_id"], "type": "Disease"}, "opentargets", row["disease_id"])
        edges.append({"a": a, "b": b, "relation": "ASSOCIATED_WITH", "props": {
            "edge_key": edge_key(version, "OpenTargets", a, "ASSOCIATED_WITH", b), "graph_version": version,
            "source": "OpenTargets", "score": row["score"], "score_kind": "source_association_not_accuracy",
            "target_id": row["target_id"], "disease_id": row["disease_id"]}})
    if len({r["props"]["edge_key"] for r in edges}) != len(edges):
        raise ValueError("Duplicate source-specific edge identity")
    return list(nodes.values()), edges


class Neo4jImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=10, max_transaction_retry_time=10)

    def verify_connectivity(self): self.driver.verify_connectivity()
    def close(self): self.driver.close()

    def setup_constraints(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT sma_entity_key_unique IF NOT EXISTS FOR (e:SMAEntity) REQUIRE e.entity_key IS UNIQUE").consume()
            session.run("CREATE CONSTRAINT sma_graph_metadata_unique IF NOT EXISTS FOR (m:SMAGraphMetadata) REQUIRE m.name IS UNIQUE").consume()

    def clear_managed_graph(self):
        raise RuntimeError("Destructive clearing is disabled. Use a new graph version; historical graphs are preserved.")

    def import_records(self, nodes, edges, batch_size=300):
        with self.driver.session() as session:
            groups = defaultdict(list)
            for node in nodes: groups[safe_label(node["type"])].append(node)
            for label, rows in sorted(groups.items()):
                query = f"UNWIND $rows AS row MERGE (n:SMAEntity:{label} {{entity_key: row.entity_key}}) SET n += row"
                for i in range(0, len(rows), batch_size): session.run(query, rows=rows[i:i + batch_size]).consume()
            groups = defaultdict(list)
            for edge in edges: groups[safe_relationship_type(edge["relation"])].append(edge)
            for relation, rows in sorted(groups.items()):
                query = f"""UNWIND $rows AS row
                MATCH (a:SMAEntity {{entity_key: row.a}})
                MATCH (b:SMAEntity {{entity_key: row.b}})
                MERGE (a)-[r:{relation} {{edge_key: row.props.edge_key}}]->(b) SET r += row.props"""
                for i in range(0, len(rows), batch_size): session.run(query, rows=rows[i:i + batch_size]).consume()

    def accept(self, nodes, edges, version):
        with self.driver.session(default_access_mode=READ_ACCESS) as session:
            actual_nodes = [r["p"] for r in session.run("MATCH (n:SMAEntity {graph_version:$v}) RETURN properties(n) AS p", v=version)]
            actual_edges = [r.data() for r in session.run("MATCH (a:SMAEntity)-[r]->(b:SMAEntity) WHERE r.graph_version=$v RETURN a.entity_key AS a,b.entity_key AS b,type(r) AS relation,properties(r) AS props", v=version)]
            legacy = session.run("MATCH (n:Entity) RETURN count(n) AS nodes").single()["nodes"]
            constraints = [r.data() for r in session.run("SHOW CONSTRAINTS YIELD name,labelsOrTypes,properties RETURN name,labelsOrTypes,properties")]
        wanted_nodes = {n["entity_key"]: n for n in nodes}
        found_nodes = {n["entity_key"]: n for n in actual_nodes}
        wanted_edges = {r["props"]["edge_key"]: r for r in edges}
        found_edges = {r["props"]["edge_key"]: r for r in actual_edges}
        checks = {"exact_node_properties_match": found_nodes == wanted_nodes,
                  "exact_relationship_properties_match": found_edges == wanted_edges,
                  "no_duplicate_nodes": len(actual_nodes) == len(found_nodes),
                  "no_duplicate_edges": len(actual_edges) == len(found_edges),
                  "typed_constraint_present": any(r["name"] == "sma_entity_key_unique" for r in constraints),
                  "all_original_evidence_records_preserved": sum(r["props"].get("evidence_count", 0) for r in actual_edges) == sum(r["props"].get("evidence_count", 0) for r in edges)}
        smn = {n["name"]: n.get("ncbi_gene") for n in actual_nodes if n["namespace"] == "literature" and n["type"] == "Gene" and n["name"] in {"SMN1", "SMN2"}}
        expected_smn = {n["name"]: n.get("ncbi_gene") for n in nodes if n["namespace"] == "literature" and n["type"] == "Gene" and n["name"] in {"SMN1", "SMN2"}}
        checks["smn1_smn2_separate_authoritative_ids"] = smn == expected_smn
        counts = {source: sum(r["props"]["source"] == source for r in actual_edges) for source in ("Literature_NLP", "OpenTargets")}
        return {"status": "passed" if all(checks.values()) else "failed", "graph_version": version,
                "checks": checks, "typed_nodes": len(actual_nodes), "nodes_by_namespace": {ns: sum(n["namespace"] == ns for n in actual_nodes) for ns in ("literature", "opentargets")},
                "relationship_counts_by_source": counts, "preserved_evidence_records": sum(r["props"].get("evidence_count", 0) for r in actual_edges),
                "legacy_entity_nodes_retained": legacy, "constraints": constraints,
                "smn_gene_ids": smn, "acceptance_kind": "live full property/identity/provenance reconciliation; not biomedical correctness"}

    def activate(self, version):
        with self.driver.session() as session:
            row = session.run("MERGE (m:SMAGraphMetadata {name:'active'}) WITH m,m.graph_version AS old SET m.previous_version=CASE WHEN old=$v THEN m.previous_version ELSE old END,m.graph_version=$v,m.activated_at=datetime() RETURN old", v=version).single()
            return row["old"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fused-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--aligned-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--quality-file", default="artifacts/runs/assertion_quality_context_fixed_2026-10-02/assertion_quality_full.jsonl")
    parser.add_argument("--opentargets-file", default="data/external/sma_gda_baseline.jsonl")
    parser.add_argument("--summary-file", required=True)
    parser.add_argument("--clear-managed-graph", action="store_true")
    args = parser.parse_args()
    if Path(args.summary_file).exists():
        parser.error("Summary already exists; choose a new dated artifact path")
    if args.clear_managed_graph: parser.error("Clearing is disabled: versioned import preserves historical graphs")
    load_local_env()
    if not all(os.getenv(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD")):
        raise RuntimeError("Required Neo4j variables missing in ignored root .env")
    inputs = {key: Path(getattr(args, key + "_file")) for key in ("fused", "aligned", "quality", "opentargets")}
    hashes = {key: sha256(path) for key, path in inputs.items()}
    version = "typed-v2-" + hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    fused, external, aligned, quality = [load_jsonl(inputs[k]) for k in ("fused", "opentargets", "aligned", "quality")]
    nodes, edges = build_import_records(fused, external, aligned, quality, version)
    importer = Neo4jImporter(os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
    summary = {"status": "not_started", "graph_version": version, "input_sha256": hashes,
               "created_utc": datetime.now(timezone.utc).isoformat(),
               "importer_code_sha256": sha256(__file__),
               "input_paths": {key: str(path.resolve()) for key, path in inputs.items()},
               "database_policy": "Separate SMAEntity label and source namespaces; legacy Entity nodes/constraints untouched", "automatic_delete": False}
    try:
        importer.verify_connectivity()
        with importer.driver.session(default_access_mode=READ_ACCESS) as session:
            before_nodes = session.run("MATCH (n:Entity) RETURN count(n) AS c").single()["c"]
            before_rels = session.run("MATCH (:Entity)-[r]->(:Entity) RETURN count(r) AS c").single()["c"]
        importer.setup_constraints(); importer.import_records(nodes, edges)
        summary.update(importer.accept(nodes, edges, version))
        with importer.driver.session(default_access_mode=READ_ACCESS) as session:
            after_rels = session.run("MATCH (:Entity)-[r]->(:Entity) RETURN count(r) AS c").single()["c"]
        summary["checks"]["legacy_graph_counts_unchanged"] = before_nodes == summary["legacy_entity_nodes_retained"] and before_rels == after_rels
        summary["legacy_relationships_retained"] = after_rels
        summary["input_hashes_unchanged"] = all(sha256(path) == hashes[key] for key, path in inputs.items())
        if summary["status"] != "passed" or not all(summary["checks"].values()) or not summary["input_hashes_unchanged"]:
            summary["status"] = "failed"; raise RuntimeError("Typed database acceptance failed; active pointer unchanged")
        summary["previous_active_version"] = importer.activate(version)
        summary["activated"] = True
    except Exception as exc:
        summary["status"] = "failed"; summary["error_class"] = type(exc).__name__
        raise
    finally:
        importer.close()
        target = Path(args.summary_file); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("status", "graph_version", "typed_nodes", "relationship_counts_by_source", "preserved_evidence_records")}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())
