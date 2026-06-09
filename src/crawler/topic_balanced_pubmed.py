import argparse
import csv
import hashlib
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crawler.pubmed_crawler import fetch_abstracts_batch, fetch_pmids, parse_medline_records


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")



def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_existing_pmids(path):
    pmids = set()
    if not Path(path).exists():
        return pmids
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("pmid"):
                pmids.add(str(data["pmid"]))
    return pmids


def build_query(topic_terms, max_terms):
    terms = [item["term"] for item in topic_terms[:max_terms] if item.get("term")]
    quoted_terms = [f'"{term}"[Title/Abstract]' for term in terms]
    if not quoted_terms:
        return '"Spinal Muscular Atrophy"[Title/Abstract]'
    return '"Spinal Muscular Atrophy"[Title/Abstract] AND (' + " OR ".join(quoted_terms) + ")"


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch additional PubMed abstracts for underrepresented topics.")
    parser.add_argument("--clustered-file", default="data/processed/clustered_abstracts.jsonl")
    parser.add_argument("--topic-terms-file", required=True)
    parser.add_argument("--source-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--min-topic-count", type=int, default=100)
    parser.add_argument("--max-topic-fetch", type=int, default=100)
    parser.add_argument("--query-terms", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser.parse_args()


def main():
    args = parse_args()
    clustered_file = (REPO_ROOT / args.clustered_file).resolve()
    topic_terms_file = (REPO_ROOT / args.topic_terms_file).resolve()
    source_file = (REPO_ROOT / args.source_file).resolve()
    if not clustered_file.exists():
        logging.error("Clustered file %s not found.", clustered_file)
        return 1
    if not topic_terms_file.exists():
        logging.error("Topic terms file %s not found.", topic_terms_file)
        return 1

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"stage1_topic_balanced_pubmed_{stamp}"
    output_file = run_dir / "outputs" / "data" / "raw" / "topic_balanced_pubmed_sma_abstracts.jsonl"
    query_file = run_dir / "topic_queries.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_json(clustered_file, lines=True)
    topic_counts = df["topic"].value_counts().to_dict()
    topic_terms = json.loads(topic_terms_file.read_text(encoding="utf-8"))
    existing_pmids = load_existing_pmids(source_file)

    topic_queries = []
    new_records = []
    seen_new = set()
    for topic_id, count in sorted(topic_counts.items(), key=lambda item: (item[1], item[0])):
        if int(topic_id) == -1 or count >= args.min_topic_count:
            continue
        terms = topic_terms.get(str(topic_id), [])
        query = build_query(terms, args.query_terms)
        pmids = fetch_pmids(query, retmax=args.max_topic_fetch)
        candidate_pmids = [pmid for pmid in pmids if str(pmid) not in existing_pmids and str(pmid) not in seen_new]
        topic_queries.append({
            "topic": int(topic_id),
            "current_count": int(count),
            "query": query,
            "returned_pmids": len(pmids),
            "new_candidate_pmids": len(candidate_pmids),
        })
        for start in range(0, len(candidate_pmids), args.batch_size):
            batch = candidate_pmids[start:start + args.batch_size]
            if not batch:
                continue
            raw_text = fetch_abstracts_batch(batch)
            records = parse_medline_records(raw_text)
            for record in records:
                pmid = str(record.get("pmid", ""))
                if not pmid or pmid in existing_pmids or pmid in seen_new:
                    continue
                seen_new.add(pmid)
                record["topic_balance_source_topic"] = int(topic_id)
                new_records.append(record)
            time.sleep(0.35)

    with output_file.open("w", encoding="utf-8") as f:
        for record in new_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    query_file.write_text(json.dumps(topic_queries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        "clustered_file": str(clustered_file.relative_to(REPO_ROOT)),
        "topic_terms_file": str(topic_terms_file.relative_to(REPO_ROOT)),
        "source_file": str(source_file.relative_to(REPO_ROOT)),
        "min_topic_count": args.min_topic_count,
        "max_topic_fetch": args.max_topic_fetch,
        "new_records": len(new_records),
        "output_file": str(output_file.relative_to(REPO_ROOT)),
        "output_sha256": sha256_file(output_file),
    }
    (run_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (run_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"])
        writer.writeheader()
        for artifact, path, records in [
            ("topic_balanced_pubmed_abstracts", output_file, len(new_records)),
            ("topic_queries", query_file, len(topic_queries)),
        ]:
            writer.writerow({
                "artifact": artifact,
                "path": str(path.relative_to(REPO_ROOT)),
                "records": records,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "notes": "not promoted to canonical raw data",
            })

    logging.info("Topic-balanced PubMed retrieval complete: %s", run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
