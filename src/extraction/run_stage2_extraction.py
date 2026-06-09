import argparse
import csv
import hashlib
import json
import logging
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from local_pipeline import rule_candidate_extraction
    from merge_triples import merge_jsonl
except ModuleNotFoundError:
    from src.extraction.local_pipeline import rule_candidate_extraction
    from src.extraction.merge_triples import merge_jsonl
from src.biomedical.schema import normalize_triple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"


def display_path(path):
    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path):
    records = []
    bad_lines = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                bad_lines.append({"line": line_no, "error": str(exc), "raw": line[:500]})
    return records, bad_lines


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def chunk_ranges(total, chunk_size):
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        yield start, end


def validate_triples(path, rejected_path=None, allow_duplicates=True, require_evidence=True):
    records, bad_lines = load_jsonl(path)
    invalid = []
    seen = set()
    duplicate_count = 0

    for idx, record in enumerate(records, 1):
        missing = []
        e1 = record.get("entity_1", {})
        e2 = record.get("entity_2", {})
        if not record.get("source_pmid"):
            missing.append("source_pmid")
        if not e1.get("name"):
            missing.append("entity_1.name")
        if not e1.get("type"):
            missing.append("entity_1.type")
        if not record.get("relation"):
            missing.append("relation")
        if not e2.get("name"):
            missing.append("entity_2.name")
        if not e2.get("type"):
            missing.append("entity_2.type")
        if not isinstance(record.get("computed_confidence"), (int, float)):
            missing.append("computed_confidence")
        extracted_by = record.get("extracted_by", "")
        if (
            "LLM" not in extracted_by
            and extracted_by not in {"Regex_Fallback", "Rule_Candidate"}
            and not str(extracted_by).startswith("Rule_Candidate")
        ):
            missing.append("extracted_by")
        _, schema_problems = normalize_triple(record, require_evidence=require_evidence)
        missing.extend(schema_problems)

        sig = (
            str(record.get("source_pmid", "")),
            str(e1.get("name", "")).lower(),
            str(record.get("relation", "")).upper(),
            str(e2.get("name", "")).lower(),
        )
        if sig in seen:
            duplicate_count += 1
        seen.add(sig)

        if missing:
            invalid.append({"line": idx, "missing_or_invalid": missing, "record": record})

    if rejected_path and (bad_lines or invalid):
        rejected_path.parent.mkdir(parents=True, exist_ok=True)
        with rejected_path.open("w", encoding="utf-8") as f:
            for item in bad_lines:
                f.write(json.dumps({"kind": "bad_json", **item}, ensure_ascii=False) + "\n")
            for item in invalid:
                f.write(json.dumps({"kind": "invalid_triple", **item}, ensure_ascii=False) + "\n")

    return {
        "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        "records": len(records),
        "bad_json_lines": len(bad_lines),
        "invalid_triples": len(invalid),
        "duplicate_stage_signature_count": duplicate_count,
        "duplicates_allowed": allow_duplicates,
        "evidence_required": require_evidence,
        "valid": len(bad_lines) == 0 and len(invalid) == 0 and (allow_duplicates or duplicate_count == 0),
        "source_counts": dict(Counter(record.get("extracted_by", "") for record in records)),
        "unique_pmids": len({str(record.get("source_pmid", "")) for record in records if record.get("source_pmid")}),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def run_llm_chunk(args, run_dir, start, end):
    chunk_name = f"llm_{start:03d}_{end - 1:03d}"
    chunk_file = run_dir / "chunks" / f"{chunk_name}.jsonl"
    log_file = run_dir / "logs" / f"{chunk_name}.log"

    if chunk_file.exists():
        validation = validate_triples(chunk_file, allow_duplicates=True, require_evidence=True)
        if validation["valid"]:
            logging.info("Skipping existing valid chunk %s", chunk_file)
            return {"chunk": chunk_name, "status": "skipped", **validation}

    log_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "src" / "extraction" / "llm_extractor.py"),
        "--input-file",
        args.input_file,
        "--output-file",
        str(chunk_file),
        "--offset",
        str(start),
        "--limit",
        str(end - start),
        "--model",
        args.model,
        "--max-tokens",
        str(args.max_tokens),
        "--min-triples",
        "0",
    ]

    logging.info("Running LLM chunk %s (%s-%s)", chunk_name, start, end - 1)
    with log_file.open("w", encoding="utf-8") as log:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)

    validation = validate_triples(
        chunk_file,
        rejected_path=run_dir / "rejected" / f"{chunk_name}_invalid.jsonl",
        allow_duplicates=True,
        require_evidence=True,
    )
    status = "completed" if proc.returncode == 0 and validation["valid"] else "failed"
    return {"chunk": chunk_name, "status": status, "exit_code": proc.returncode, **validation}


def build_split(input_file, llm_limit, model, chunk_size):
    records, bad_lines = load_jsonl(input_file)
    if bad_lines:
        raise ValueError(f"Input file has {len(bad_lines)} invalid JSON lines: {input_file}")
    pmids = [str(record.get("pmid", "")) for record in records]
    effective_llm_limit = len(records) if llm_limit < 0 else min(llm_limit, len(records))
    return {
        "input_file": display_path(input_file),
        "input_sha256": sha256_file(input_file),
        "input_records": len(records),
        "llm_model": model,
        "chunk_size": chunk_size,
        "requested_llm_limit": llm_limit,
        "effective_llm_limit": effective_llm_limit,
        "llm_pmids": pmids[:effective_llm_limit],
        "rule_candidate_pmids": pmids[effective_llm_limit:],
    }, records


def run_rule_candidates(records, llm_limit, output_file):
    triples = []
    for record in records[llm_limit:]:
        pmid = str(record.get("pmid", ""))
        abstract = record.get("abstract", "")
        if not abstract:
            continue
        seen = set()
        for triple in rule_candidate_extraction(abstract, pmid):
            sig = (
                triple["entity_1"]["name"],
                triple["relation"],
                triple["entity_2"]["name"],
            )
            if sig in seen:
                continue
            seen.add(sig)
            triples.append(triple)
    write_jsonl(output_file, triples)
    return triples


def write_manifest(run_dir, validations):
    manifest_file = run_dir / "manifest.csv"
    rows = []
    for item in validations:
        path = Path(item["path"])
        rows.append(
            {
                "path": item["path"],
                "records": item["records"],
                "bad_json_lines": item["bad_json_lines"],
                "invalid_triples": item["invalid_triples"],
                "duplicate_stage_signature_count": item["duplicate_stage_signature_count"],
                "unique_pmids": item["unique_pmids"],
                "bytes": item["bytes"],
                "sha256": item["sha256"],
                "valid": item["valid"],
                "source_counts": json.dumps(item["source_counts"], sort_keys=True),
            }
        )
    with manifest_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def promote_outputs(run_dir, outputs):
    for source, dest in outputs:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        logging.info("Promoted %s -> %s", source, dest)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Stage 2 extraction with chunk/resume/validate/promote.")
    parser.add_argument("--input-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument(
        "--llm-limit",
        type=int,
        default=-1,
        help="Number of abstracts assigned to LLM extraction. Use -1 for all input records.",
    )
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--parallel-workers", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--promote", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = (REPO_ROOT / args.input_file).resolve()
    if args.run_dir:
        run_dir = (REPO_ROOT / args.run_dir).resolve()
    else:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        run_dir = REPO_ROOT / "artifacts" / "runs" / f"stage2_extraction_full_{stamp}"

    run_dir.mkdir(parents=True, exist_ok=True)
    for subdir in ("chunks", "logs", "outputs/data/processed", "rejected"):
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    split, records = build_split(input_file, args.llm_limit, args.model, args.chunk_size)
    write_json(run_dir / "stage2_input_split.json", split)

    chunk_results = []
    ranges = list(chunk_ranges(len(split["llm_pmids"]), args.chunk_size))
    worker_count = max(1, args.parallel_workers)
    if worker_count == 1 or len(ranges) <= 1:
        for start, end in ranges:
            result = run_llm_chunk(args, run_dir, start, end)
            chunk_results.append(result)
            if result["status"] == "failed":
                write_json(run_dir / "validation_summary.json", {"valid": False, "chunk_results": chunk_results})
                logging.error("Stopping because chunk %s failed", result["chunk"])
                return 1
    else:
        logging.info("Running %s LLM chunks with %s parallel workers.", len(ranges), worker_count)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_range = {
                executor.submit(run_llm_chunk, args, run_dir, start, end): (start, end)
                for start, end in ranges
            }
            for future in as_completed(future_to_range):
                result = future.result()
                chunk_results.append(result)
        chunk_results.sort(key=lambda item: item["chunk"])
        failed_chunks = [item for item in chunk_results if item["status"] == "failed"]
        if failed_chunks:
            write_json(run_dir / "validation_summary.json", {"valid": False, "chunk_results": chunk_results})
            logging.error("Stopping because %s LLM chunks failed.", len(failed_chunks))
            return 1

    llm_output = run_dir / "outputs" / "data" / "processed" / "llm_extracted_triples.jsonl"
    with llm_output.open("w", encoding="utf-8") as out:
        for start, end in chunk_ranges(len(split["llm_pmids"]), args.chunk_size):
            chunk_file = run_dir / "chunks" / f"llm_{start:03d}_{end - 1:03d}.jsonl"
            if chunk_file.exists():
                out.write(chunk_file.read_text(encoding="utf-8"))

    rule_candidate_output = run_dir / "outputs" / "data" / "interim" / "rule_candidate_triples.jsonl"
    rule_candidate_output.parent.mkdir(parents=True, exist_ok=True)
    effective_llm_limit = len(split["llm_pmids"])
    rule_candidate_triples = run_rule_candidates(records, effective_llm_limit, rule_candidate_output)
    logging.info("Rule candidate extraction wrote %s candidates", len(rule_candidate_triples))

    canonical_output = run_dir / "outputs" / "data" / "processed" / "extracted_triples.jsonl"
    merge_jsonl([str(llm_output)], str(canonical_output))

    validations = [
        validate_triples(llm_output, run_dir / "rejected" / "llm_invalid.jsonl", allow_duplicates=True, require_evidence=True),
        validate_triples(rule_candidate_output, run_dir / "rejected" / "rule_candidate_invalid.jsonl", allow_duplicates=True, require_evidence=True),
        validate_triples(canonical_output, run_dir / "rejected" / "canonical_llm_invalid.jsonl", allow_duplicates=False, require_evidence=True),
    ]
    all_valid = all(item["valid"] for item in validations)
    summary = {
        "valid": all_valid,
        "model": args.model,
        "chunk_size": args.chunk_size,
        "llm_limit_requested": args.llm_limit,
        "llm_limit_effective": effective_llm_limit,
        "parallel_workers": worker_count,
        "canonical_policy": "LLM-only; rule candidates are auxiliary and not merged into extracted_triples.jsonl",
        "chunk_results": chunk_results,
        "outputs": validations,
    }
    write_json(run_dir / "validation_summary.json", summary)
    write_manifest(run_dir, validations)

    readme = run_dir / "README.md"
    readme.write_text(
        "# Stage 2 Extraction Full Run\n\n"
        f"- Model: `{args.model}`\n"
        f"- Input: `{args.input_file}`\n"
        f"- LLM PMIDs: {len(split['llm_pmids'])}\n"
        f"- Requested LLM limit: {args.llm_limit}\n"
        f"- Rule candidate PMIDs: {len(split['rule_candidate_pmids'])}\n"
        f"- Parallel workers: {worker_count}\n"
        "- Canonical policy: `LLM-only extracted_triples.jsonl`; rule candidates are auxiliary\n"
        f"- Validation: {'passed' if all_valid else 'failed'}\n"
        f"- Promoted: {bool(args.promote and all_valid)}\n",
        encoding="utf-8",
    )

    if not all_valid:
        logging.error("Validation failed; canonical outputs were not promoted.")
        return 1

    if args.promote:
        promote_outputs(
            run_dir,
            [
                (llm_output, REPO_ROOT / "data" / "processed" / "llm_extracted_triples.jsonl"),
                (rule_candidate_output, REPO_ROOT / "data" / "interim" / "rule_candidate_triples.jsonl"),
                (canonical_output, REPO_ROOT / "data" / "processed" / "extracted_triples.jsonl"),
            ],
        )

    logging.info("Stage 2 extraction run completed successfully: %s", run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
