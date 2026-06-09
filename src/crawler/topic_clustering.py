import argparse
import csv
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
except ImportError:
    BERTopic = None
    SentenceTransformer = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "NeuML/pubmedbert-base-embeddings"


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(description="Cluster PubMed SMA abstracts with biomedical BERTopic.")
    parser.add_argument("--input-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--output-file", default="")
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--topic-terms-file", default="")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--min-topic-size", type=int, default=15)
    parser.add_argument("--min-df", type=int, default=2)
    parser.add_argument("--max-df", type=float, default=0.85)
    parser.add_argument("--ngram-min", type=int, default=1)
    parser.add_argument("--ngram-max", type=int, default=3)
    parser.add_argument("--promote", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if BERTopic is None or SentenceTransformer is None:
        logging.error("BERTopic and sentence-transformers must be installed before topic clustering.")
        return 1

    input_file = (REPO_ROOT / args.input_file).resolve()
    if not input_file.exists():
        logging.error("Input file %s not found.", input_file)
        return 1

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"stage1_topic_clustering_{stamp}"
    output_file = Path(args.output_file) if args.output_file else run_dir / "outputs" / "data" / "processed" / "clustered_abstracts.jsonl"
    summary_file = Path(args.summary_file) if args.summary_file else run_dir / "topic_summary.csv"
    topic_terms_file = Path(args.topic_terms_file) if args.topic_terms_file else run_dir / "topic_terms.json"
    for path in (output_file, summary_file, topic_terms_file):
        path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_json(input_file, lines=True)
    df = df.dropna(subset=["abstract"])
    df = df[df["abstract"].astype(str).str.strip() != ""].copy()
    logging.info("Loaded %s abstracts for clustering.", len(df))

    abstracts = df["abstract"].astype(str).tolist()
    vectorizer_model = CountVectorizer(
        stop_words=None,
        ngram_range=(args.ngram_min, args.ngram_max),
        min_df=args.min_df,
        max_df=args.max_df,
    )
    embedding_model = SentenceTransformer(args.model)
    topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        min_topic_size=args.min_topic_size,
        calculate_probabilities=False,
        verbose=True,
    )

    topics, _ = topic_model.fit_transform(abstracts)
    df["topic"] = topics
    df.to_json(output_file, orient="records", lines=True, force_ascii=False)

    topic_info = topic_model.get_topic_info()
    topic_info.to_csv(summary_file, index=False)
    topic_terms = {}
    for topic_id in topic_info["Topic"].tolist():
        if topic_id == -1:
            continue
        topic_terms[str(topic_id)] = [
            {"term": term, "weight": weight}
            for term, weight in topic_model.get_topic(topic_id)[:15]
        ]
    topic_terms_file.write_text(json.dumps(topic_terms, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = {
        "input_file": str(input_file.relative_to(REPO_ROOT)),
        "input_sha256": sha256_file(input_file),
        "records": len(df),
        "model": args.model,
        "vectorizer": {
            "stop_words": None,
            "ngram_range": [args.ngram_min, args.ngram_max],
            "min_df": args.min_df,
            "max_df": args.max_df,
        },
        "output_file": str(output_file.relative_to(REPO_ROOT)),
        "summary_file": str(summary_file.relative_to(REPO_ROOT)),
        "topic_terms_file": str(topic_terms_file.relative_to(REPO_ROOT)),
        "output_sha256": sha256_file(output_file),
    }
    (run_dir / "validation_summary.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (run_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"])
        writer.writeheader()
        for artifact, path in [
            ("clustered_abstracts", output_file),
            ("topic_summary", summary_file),
            ("topic_terms", topic_terms_file),
        ]:
            writer.writerow({
                "artifact": artifact,
                "path": str(path.relative_to(REPO_ROOT)),
                "records": len(df) if artifact == "clustered_abstracts" else "",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "notes": "domain-aware vectorizer without static stop-word removal",
            })

    if args.promote:
        canonical = REPO_ROOT / "data" / "processed" / "clustered_abstracts.jsonl"
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output_file, canonical)
        logging.info("Promoted %s -> %s", output_file, canonical)

    logging.info("Topic clustering complete: %s", run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
