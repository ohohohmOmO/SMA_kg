"""Build an offline, bounded graph with complete source evidence, without Neo4j."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.audit_fyp_inputs import load_jsonl, signature
from src.evaluation.fyp_dataset import sha256


def assemble(raw, aligned, fused, sources, validations, external):
    if len(raw) != len(aligned) or len(raw) != len(validations):
        raise ValueError("Raw/aligned/validation counts differ")
    nodes, node_ids, edges, groups = [], {}, [], defaultdict(list)

    def node(entity, namespace="literature", source_id=""):
        key = (namespace, entity["name"], entity["type"], source_id)
        if key not in node_ids:
            node_ids[key] = len(nodes)
            nodes.append({"name": entity["name"], "type": entity["type"],
                          "namespace": namespace, "source_id": source_id})
        return node_ids[key]

    for index, (original, normalized, validation) in enumerate(zip(raw, aligned, validations), 1):
        if (validation["raw_record_number"] != index or
                str(validation["source_pmid"]) != str(original["source_pmid"]) or
                str(normalized["source_pmid"]) != str(original["source_pmid"]) or
                validation["triple"] != {k: original[k] for k in ("entity_1", "relation", "entity_2")} or
                original["evidence_text"] != normalized["evidence_text"]):
            raise ValueError("Source/validation row identity differs")
        pmid = str(original["source_pmid"])
        if pmid not in sources:
            raise ValueError("Missing abstract snapshot")
        groups[signature(normalized)].append({"raw_record_number": index, "pmid": pmid,
            "original_entity_1": original["entity_1"], "original_entity_2": original["entity_2"],
            "span": original["evidence_text"], "validation": validation["validation"]})
    seen = set()
    for row in fused:
        key = signature(row)
        records = groups.get(key, [])
        if (key in seen or not records or len(records) != row["evidence"]["evidence_count"] or
                {r["pmid"] for r in records} != set(map(str, row["evidence"]["pmid_list"]))):
            raise ValueError("Fused source join is incomplete or duplicated")
        seen.add(key)
        edges.append({"a": node(row["entity_1"]), "b": node(row["entity_2"]),
            "relation": row["relation"], "source": "literature",
            "needs_review": row.get("review_status") == "needs_review",
            "confidence": row.get("computed_confidence"), "records": records,
            "pmids": sorted({r["pmid"] for r in records})})
    if seen != set(groups):
        raise ValueError("Some extraction groups are absent from fused edges")
    for row in external:
        gene = {"name": row["gene_symbol"], "type": "Gene"}
        disease = {"name": row["disease_id"], "type": "Disease"}
        edges.append({"a": node(gene, "opentargets", row["target_id"]),
            "b": node(disease, "opentargets", row["disease_id"]),
            "relation": "ASSOCIATED_WITH", "source": "opentargets", "needs_review": False,
            "score": row["score"], "target_id": row["target_id"], "disease_id": row["disease_id"]})
    return {"nodes": nodes, "edges": edges, "sources": sources,
            "literature_edge_count": len(fused), "external_edge_count": len(external),
            "original_evidence_count": len(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    out = (ROOT / args.run_dir).resolve()
    paths = {"raw": ROOT / "data/processed/extracted_triples.jsonl",
             "aligned": ROOT / "data/interim/aligned_triples.jsonl",
             "fused": ROOT / "data/processed/fused_triples.jsonl",
             "sources": ROOT / "data/raw/pubmed_sma_abstracts.jsonl",
             "validations": out / "evidence_validation_full.jsonl",
             "external": ROOT / "data/external/sma_gda_baseline.jsonl"}
    hashes = {name: sha256(path) for name, path in paths.items()}
    values = {}
    for name, path in paths.items():
        values[name], errors = load_jsonl(path)
        if errors:
            raise ValueError(f"Invalid JSONL: {name}")
    values["sources"] = {str(row["pmid"]): {key: row.get(key, "") for key in ("title", "abstract")}
                         for row in values["sources"]}
    data = assemble(**values)
    data["run"] = out.name
    template = Path(__file__).with_name("fyp_graph_template.html")
    html = template.read_text(encoding="utf-8").replace("__GRAPH_DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
    target = out / "graph_explorer.html"
    target.write_text(html, encoding="utf-8")
    if any(sha256(path) != hashes[name] for name, path in paths.items()):
        raise ValueError("Input changed while building graph")
    manifest = {"builder_sha256": sha256(__file__), "template_sha256": sha256(template),
                "inputs": {name: {"path": str(path), "sha256": hashes[name]} for name, path in paths.items()},
                "output_sha256": sha256(target), "nodes_by_namespace": {
                    ns: sum(n["namespace"] == ns for n in data["nodes"]) for ns in ("literature", "opentargets")},
                "literature_edges": len(values["fused"]), "external_edges": len(values["external"]),
                "original_evidence_records_joined": len(values["raw"]),
                "identity_policy": "Literature name+type; external source identifiers in separate namespace. No inferred cross-source entity merge.",
                "database_access": False, "external_resources_required": False}
    (out / "graph_explorer_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(target), "literature_edges": manifest["literature_edges"],
                      "external_edges": manifest["external_edges"], "joined_records": len(values["raw"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
