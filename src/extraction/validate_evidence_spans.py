import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.confidence import normalize_and_score
from src.biomedical.evidence import DEFAULT_MIN_FUZZY_SCORE, align_evidence_span
from src.evidence.loaders import load_abstracts_by_pmid


def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit extracted triple evidence spans against their source PubMed abstracts."
    )
    parser.add_argument("--input-file", default="data/processed/extracted_triples.jsonl")
    parser.add_argument("--abstracts-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--min-fuzzy-score", type=float, default=DEFAULT_MIN_FUZZY_SCORE)
    return parser.parse_args()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path):
    path = Path(path)
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def audit_evidence_spans(input_file, abstracts_file, run_dir, min_fuzzy_score):
    input_file = Path(input_file)
    abstracts_file = Path(abstracts_file)
    run_dir = Path(run_dir)
    output_file = run_dir / "outputs" / "data" / "processed" / "evidence_aligned_triples.jsonl"
    rejected_file = run_dir / "rejected" / "evidence_span_rejected.jsonl"
    summary_file = run_dir / "validation_summary.json"
    manifest_file = run_dir / "manifest.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    rejected_file.parent.mkdir(parents=True, exist_ok=True)

    abstracts = load_abstracts_by_pmid(abstracts_file)
    total = 0
    aligned_count = 0
    rejected_count = 0
    bad_json_lines = 0
    method_counts = Counter()
    rejection_counts = Counter()

    with (
        input_file.open("r", encoding="utf-8") as source,
        output_file.open("w", encoding="utf-8") as accepted,
        rejected_file.open("w", encoding="utf-8") as rejected,
    ):
        for line_no, line in enumerate(source, 1):
            if not line.strip():
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                bad_json_lines += 1
                rejected_count += 1
                rejection_counts["bad_json"] += 1
                rejected.write(json.dumps({
                    "line": line_no,
                    "reason": "bad_json",
                    "error": str(exc),
                }, ensure_ascii=False) + "\n")
                continue

            pmid = str(record.get("source_pmid", "")).strip()
            source_abstract = abstracts.get(pmid)
            if not source_abstract:
                rejected_count += 1
                rejection_counts["missing_abstract"] += 1
                rejected.write(json.dumps({
                    "line": line_no,
                    "reason": "missing_abstract",
                    "source_pmid": pmid,
                    "record": record,
                }, ensure_ascii=False) + "\n")
                continue

            alignment = align_evidence_span(
                record.get("evidence_text", ""),
                source_abstract.get("abstract", ""),
                min_fuzzy_score=min_fuzzy_score,
            )
            if not alignment["valid"]:
                rejected_count += 1
                rejection_counts["evidence_text_not_aligned_to_abstract"] += 1
                rejected.write(json.dumps({
                    "line": line_no,
                    "reason": "evidence_text_not_aligned_to_abstract",
                    "source_pmid": pmid,
                    "alignment": alignment,
                    "record": record,
                }, ensure_ascii=False) + "\n")
                continue

            record["evidence_alignment"] = alignment
            normalized, problems = normalize_and_score(record, require_evidence=True)
            if problems:
                rejected_count += 1
                rejection_counts["schema_invalid"] += 1
                rejected.write(json.dumps({
                    "line": line_no,
                    "reason": "schema_invalid",
                    "source_pmid": pmid,
                    "problems": problems,
                    "record": record,
                }, ensure_ascii=False) + "\n")
                continue

            accepted.write(json.dumps(normalized, ensure_ascii=False) + "\n")
            aligned_count += 1
            method_counts[alignment["method"]] += 1

    summary = {
        "valid": bad_json_lines == 0,
        "input_file": display_path(input_file),
        "input_sha256": sha256_file(input_file),
        "abstracts_file": display_path(abstracts_file),
        "abstracts_sha256": sha256_file(abstracts_file),
        "min_fuzzy_score": float(min_fuzzy_score),
        "records_total": total,
        "records_aligned": aligned_count,
        "records_rejected": rejected_count,
        "alignment_rate": round(aligned_count / total, 6) if total else 0.0,
        "alignment_methods": dict(sorted(method_counts.items())),
        "rejection_reasons": dict(sorted(rejection_counts.items())),
        "bad_json_lines": bad_json_lines,
        "output_file": display_path(output_file),
        "rejected_file": display_path(rejected_file),
        "canonical_mutated": False,
    }
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with manifest_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"],
        )
        writer.writeheader()
        for artifact, path, records, notes in [
            ("evidence_aligned_triples", output_file, aligned_count, "non-canonical evidence-aligned triples"),
            ("evidence_span_rejected", rejected_file, rejected_count, "records requiring review"),
            ("validation_summary", summary_file, 1, "evidence span audit summary"),
        ]:
            writer.writerow({
                "artifact": artifact,
                "path": display_path(path),
                "records": records,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "notes": notes,
            })
    return summary


def main():
    args = parse_args()
    input_file = (REPO_ROOT / args.input_file).resolve()
    abstracts_file = (REPO_ROOT / args.abstracts_file).resolve()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = (
        (REPO_ROOT / args.run_dir).resolve()
        if args.run_dir
        else REPO_ROOT / "artifacts" / "runs" / f"evidence_span_audit_{stamp}"
    )
    if not input_file.exists() or not abstracts_file.exists():
        print("Input triples or abstracts file is missing.", file=sys.stderr)
        return 1
    summary = audit_evidence_spans(
        input_file,
        abstracts_file,
        run_dir,
        args.min_fuzzy_score,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
