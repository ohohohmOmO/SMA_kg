import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evidence.loaders import count_jsonl_records, sha256_file, write_json


DEFAULT_INPUTS = [
    "data/raw/pubmed_sma_abstracts.jsonl",
    "data/interim/aligned_triples.jsonl",
    "data/processed/fused_triples.jsonl",
    "data/interim/relation_conflicts.jsonl",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Write a Graph RAG local retrieval index manifest.")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--manifest-file", default="data/processed/graph_rag_index_manifest.json")
    parser.add_argument("--mode", default="lexical_entity")
    return parser.parse_args()


def main():
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"graph_rag_index_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = REPO_ROOT / args.manifest_file
    inputs = []
    for rel in DEFAULT_INPUTS:
        path = REPO_ROOT / rel
        inputs.append({
            "path": rel,
            "records": count_jsonl_records(path),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256_file(path) if path.exists() else "",
        })
    manifest = {
        "index_kind": "manifest_only",
        "retrieval_mode": args.mode,
        "created_at": stamp,
        "inputs": inputs,
        "notes": "Lexical/entity retrieval reads canonical JSONL files directly; no opaque vector index is required for v1.",
    }
    write_json(manifest_file, manifest)
    write_json(run_dir / "validation_summary.json", {"valid": True, "manifest_file": str(manifest_file.relative_to(REPO_ROOT)), "inputs": inputs})
    write_csv_manifest(run_dir / "manifest.csv", inputs, manifest_file)
    return 0


def write_csv_manifest(path, inputs, manifest_file):
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"])
        writer.writeheader()
        for item in inputs:
            writer.writerow({"artifact": "input", **item, "notes": "Graph RAG retrieval source"})
        writer.writerow({
            "artifact": "graph_rag_index_manifest",
            "path": str(manifest_file.relative_to(REPO_ROOT)),
            "records": "",
            "bytes": manifest_file.stat().st_size,
            "sha256": sha256_file(manifest_file),
            "notes": "manifest-only lexical/entity index",
        })


if __name__ == "__main__":
    raise SystemExit(main())

