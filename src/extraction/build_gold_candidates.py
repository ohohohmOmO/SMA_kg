import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.schema import normalize_triple




def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path):
    records = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_abstracts(path):
    abstracts = {}
    for record in load_jsonl(path):
        pmid = str(record.get("pmid", ""))
        if pmid:
            abstracts[pmid] = {
                "title": record.get("title", ""),
                "abstract": record.get("abstract", ""),
                "pub_date": record.get("pub_date", ""),
            }
    return abstracts


def stratified_candidates(triples, limit):
    buckets = defaultdict(list)
    for triple in triples:
        normalized, problems = normalize_triple(triple, require_evidence=False)
        if problems:
            continue
        key = (normalized.get("relation", ""), normalized.get("extracted_by", "UNKNOWN"))
        buckets[key].append(normalized)
    for key in buckets:
        buckets[key].sort(key=lambda item: (-float(item.get("computed_confidence", 0.0)), str(item.get("source_pmid", ""))))

    queues = [deque(items) for _, items in sorted(buckets.items())]
    selected = []
    seen = set()
    while queues and len(selected) < limit:
        next_queues = []
        for queue in queues:
            if not queue:
                continue
            item = queue.popleft()
            sig = (
                item.get("source_pmid", ""),
                item["entity_1"]["name"].lower(),
                item["relation"],
                item["entity_2"]["name"].lower(),
            )
            if sig not in seen:
                seen.add(sig)
                selected.append(item)
                if len(selected) >= limit:
                    break
            if queue:
                next_queues.append(queue)
        queues = next_queues
    return selected


def parse_args():
    parser = argparse.ArgumentParser(description="Build review-ready gold-standard candidates for RE fine-tuning.")
    parser.add_argument("--triples-file", default="data/processed/extracted_triples.jsonl")
    parser.add_argument("--abstracts-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--limit", type=int, default=750)
    return parser.parse_args()


def main():
    args = parse_args()
    triples_file = (REPO_ROOT / args.triples_file).resolve()
    abstracts_file = (REPO_ROOT / args.abstracts_file).resolve()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"stage2_gold_candidates_{stamp}"
    output_file = run_dir / "gold_candidates.jsonl"
    csv_file = run_dir / "gold_candidates.csv"
    run_dir.mkdir(parents=True, exist_ok=True)

    triples = load_jsonl(triples_file)
    abstracts = load_abstracts(abstracts_file)
    selected = stratified_candidates(triples, args.limit)

    review_rows = []
    for idx, triple in enumerate(selected, 1):
        pmid = str(triple.get("source_pmid", ""))
        source = abstracts.get(pmid, {})
        row = {
            "candidate_id": f"SMA-RE-{idx:04d}",
            "source_pmid": pmid,
            "title": source.get("title", ""),
            "abstract": source.get("abstract", ""),
            "entity_1_name": triple["entity_1"]["name"],
            "entity_1_type": triple["entity_1"]["type"],
            "relation": triple["relation"],
            "entity_2_name": triple["entity_2"]["name"],
            "entity_2_type": triple["entity_2"]["type"],
            "evidence_text": triple.get("evidence_text", ""),
            "computed_confidence": triple.get("computed_confidence", ""),
            "extracted_by": triple.get("extracted_by", ""),
            "review_status": "pending_review",
            "gold_label": "",
            "review_notes": "",
        }
        review_rows.append(row)

    with output_file.open("w", encoding="utf-8") as f:
        for row in review_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(review_rows[0].keys()) if review_rows else [])
        if review_rows:
            writer.writeheader()
            writer.writerows(review_rows)

    summary = {
        "triples_file": str(triples_file.relative_to(REPO_ROOT)),
        "abstracts_file": str(abstracts_file.relative_to(REPO_ROOT)),
        "candidate_count": len(review_rows),
        "target_use": "manual gold standard before BioBERT/UIE-med fine-tuning",
        "fine_tuning_recommendation": "Do not fine-tune until this candidate set is reviewed and baseline errors justify model training.",
    }
    (run_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (run_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"])
        writer.writeheader()
        for artifact, path in [("gold_candidates_jsonl", output_file), ("gold_candidates_csv", csv_file)]:
            writer.writerow({
                "artifact": artifact,
                "path": str(path.relative_to(REPO_ROOT)),
                "records": len(review_rows),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "notes": "pending manual review",
            })
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
