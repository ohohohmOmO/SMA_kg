import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict, deque
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


def triple_signature(item):
    return (
        str(item.get("source_pmid", "")),
        item["entity_1"]["name"].lower(),
        item["relation"],
        item["entity_2"]["name"].lower(),
    )


def normalized_unique_candidates(triples):
    candidates = []
    seen = set()
    for triple in triples:
        normalized, problems = normalize_triple(triple, require_evidence=False)
        if problems:
            continue
        sig = triple_signature(normalized)
        if sig in seen:
            continue
        seen.add(sig)
        candidates.append(normalized)
    return candidates


def evidence_exact_match(item, abstracts):
    evidence = str(item.get("evidence_text", "")).strip()
    if not evidence:
        return False
    source = abstracts.get(str(item.get("source_pmid", "")), {})
    source_text = f"{source.get('title', '')} {source.get('abstract', '')}".casefold()
    return evidence.casefold() in source_text


def stratified_candidates(triples, limit):
    buckets = defaultdict(list)
    for normalized in normalized_unique_candidates(triples):
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
            sig = triple_signature(item)
            if sig not in seen:
                seen.add(sig)
                selected.append({**item, "sample_group": "balanced_relation"})
                if len(selected) >= limit:
                    break
            if queue:
                next_queues.append(queue)
        queues = next_queues
    return selected


def evaluation_challenge_candidates(triples, abstracts, limit, primary_count, seed):
    """Build a representative primary sample plus a separate diagnostic challenge set.

    The primary sample supports an unbiased overall precision estimate. The challenge
    set deliberately over-samples low-confidence, non-exact-evidence, and rare-relation
    cases and must be reported separately from the primary result.
    """
    candidates = normalized_unique_candidates(triples)
    if limit > len(candidates):
        limit = len(candidates)
    primary_count = max(0, min(primary_count, limit))

    rng = random.Random(seed)
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    primary = [{**item, "sample_group": "primary_random"} for item in shuffled[:primary_count]]
    primary_signatures = {triple_signature(item) for item in primary}

    relation_counts = Counter(item["relation"] for item in candidates)
    challenge_buckets = defaultdict(list)
    for item in candidates:
        if triple_signature(item) in primary_signatures:
            continue
        confidence = float(item.get("computed_confidence", 0.0) or 0.0)
        exact = evidence_exact_match(item, abstracts)
        challenge_buckets[item["relation"]].append((
            0 if confidence < 0.9 else 1,
            0 if not exact else 1,
            confidence,
            rng.random(),
            item,
        ))

    for relation in challenge_buckets:
        challenge_buckets[relation].sort(key=lambda entry: entry[:4])

    queues = [
        deque(entry[-1] for entry in challenge_buckets[relation])
        for relation in sorted(challenge_buckets, key=lambda name: (relation_counts[name], name))
    ]
    challenge = []
    challenge_target = limit - primary_count
    while queues and len(challenge) < challenge_target:
        next_queues = []
        for queue in queues:
            if not queue:
                continue
            challenge.append({**queue.popleft(), "sample_group": "challenge"})
            if len(challenge) >= challenge_target:
                break
            if queue:
                next_queues.append(queue)
        queues = next_queues

    selected = primary + challenge
    review_count = min(len(selected), round(len(selected) * 0.20))
    review_rng = random.Random(seed + 1)
    second_review_indexes = set(review_rng.sample(range(len(selected)), review_count))
    return [
        {**item, "requires_second_review": index in second_review_indexes}
        for index, item in enumerate(selected)
    ]


def parse_args():
    parser = argparse.ArgumentParser(description="Build review-ready gold-standard candidates for RE fine-tuning.")
    parser.add_argument("--triples-file", default="data/processed/extracted_triples.jsonl")
    parser.add_argument("--abstracts-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--limit", type=int, default=750)
    parser.add_argument(
        "--sampling-strategy",
        choices=("balanced_relation", "evaluation_challenge"),
        default="balanced_relation",
    )
    parser.add_argument(
        "--primary-count",
        type=int,
        default=-1,
        help="Representative random sample size for evaluation_challenge; defaults to 75%% of limit.",
    )
    parser.add_argument("--seed", type=int, default=42)
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
    primary_count = args.primary_count if args.primary_count >= 0 else round(args.limit * 0.75)
    if args.sampling_strategy == "evaluation_challenge":
        selected = evaluation_challenge_candidates(
            triples,
            abstracts,
            args.limit,
            primary_count,
            args.seed,
        )
    else:
        selected = stratified_candidates(triples, args.limit)

    review_rows = []
    for idx, triple in enumerate(selected, 1):
        pmid = str(triple.get("source_pmid", ""))
        source = abstracts.get(pmid, {})
        row = {
            "candidate_id": f"SMA-RE-{idx:04d}",
            "sample_group": triple.get("sample_group", args.sampling_strategy),
            "requires_second_review": "yes" if triple.get("requires_second_review", False) else "no",
            "source_pmid": pmid,
            "title": source.get("title", ""),
            "abstract": source.get("abstract", ""),
            "entity_1_name": triple["entity_1"]["name"],
            "entity_1_type": triple["entity_1"]["type"],
            "relation": triple["relation"],
            "entity_2_name": triple["entity_2"]["name"],
            "entity_2_type": triple["entity_2"]["type"],
            "evidence_text": triple.get("evidence_text", ""),
            "evidence_exact_match": "yes" if evidence_exact_match(triple, abstracts) else "no",
            "computed_confidence": triple.get("computed_confidence", ""),
            "extracted_by": triple.get("extracted_by", ""),
            "review_status": "pending_review",
            "support_label": "",
            "entity_1_correct": "",
            "entity_2_correct": "",
            "relation_correct": "",
            "direction_correct": "",
            "evidence_span_correct": "",
            "error_type": "",
            "corrected_triple": "",
            "reviewer_id": "",
            "review_date": "",
            "review_notes": "",
            "second_reviewer_id": "",
            "second_support_label": "",
            "second_review_date": "",
            "second_review_notes": "",
            "adjudicated_label": "",
            "adjudication_notes": "",
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
        "sampling_strategy": args.sampling_strategy,
        "random_seed": args.seed,
        "primary_random_count": sum(row["sample_group"] == "primary_random" for row in review_rows),
        "challenge_count": sum(row["sample_group"] == "challenge" for row in review_rows),
        "second_review_count": sum(row["requires_second_review"] == "yes" for row in review_rows),
        "target_use": "manual gold standard before BioBERT/UIE-med fine-tuning",
        "reporting_note": "Report primary_random metrics separately from challenge-set error analysis.",
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
