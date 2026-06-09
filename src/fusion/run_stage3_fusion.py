import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
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


def validate_jsonl(path, require_core=True):
    records = 0
    bad_json = 0
    invalid = 0
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        records += 1
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            bad_json += 1
            continue
        if require_core:
            _, problems = normalize_triple(data, require_evidence=False)
            if problems:
                invalid += 1
    return {
        "path": str(Path(path).relative_to(REPO_ROOT)),
        "records": records,
        "bad_json_lines": bad_json,
        "invalid_triples": invalid,
        "bytes": Path(path).stat().st_size,
        "sha256": sha256_file(path),
        "valid": bad_json == 0 and invalid == 0,
    }


def run_command(name, cmd, log_file):
    result = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    log_file.write_text((result.stdout or "") + (result.stderr or ""), encoding="utf-8")
    return {"name": name, "exit_code": result.returncode, "log": str(log_file.relative_to(REPO_ROOT))}


def write_manifest(run_dir, validations):
    with (run_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "records", "bad_json_lines", "invalid_triples", "bytes", "sha256", "valid"])
        writer.writeheader()
        writer.writerows(validations)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Stage 3 mapping, alignment, aggregation, and validation.")
    parser.add_argument("--input-file", default="data/processed/extracted_triples.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--alignment-model", default="NeuML/pubmedbert-base-embeddings")
    parser.add_argument("--promote", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"stage3_fusion_{stamp}"
    outputs = run_dir / "outputs"
    logs = run_dir / "logs"
    mapped = outputs / "data" / "interim" / "mapped_triples.jsonl"
    aligned = outputs / "data" / "interim" / "aligned_triples.jsonl"
    fused = outputs / "data" / "processed" / "fused_triples.jsonl"
    conflicts = outputs / "data" / "interim" / "relation_conflicts.jsonl"
    rejected = outputs / "data" / "interim" / "aggregation_rejected.jsonl"
    for path in (mapped, aligned, fused, conflicts, rejected):
        path.parent.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    commands = [
        run_command(
            "dictionary_mapper",
            [
                sys.executable,
                "src/fusion/dictionary_mapper.py",
                "--input-file",
                args.input_file,
                "--output-file",
                str(mapped),
            ],
            logs / "dictionary_mapper.log",
        ),
        run_command(
            "semantic_aligner",
            [
                sys.executable,
                "src/fusion/semantic_aligner.py",
                "--input-file",
                str(mapped),
                "--output-file",
                str(aligned),
                "--model",
                args.alignment_model,
            ],
            logs / "semantic_aligner.log",
        ),
        run_command(
            "triples_aggregator",
            [
                sys.executable,
                "src/fusion/triples_aggregator.py",
                "--input-file",
                str(aligned),
                "--output-file",
                str(fused),
                "--conflict-file",
                str(conflicts),
                "--rejected-file",
                str(rejected),
            ],
            logs / "triples_aggregator.log",
        ),
    ]

    validations = [
        validate_jsonl(mapped),
        validate_jsonl(aligned),
        validate_jsonl(fused, require_core=False),
        validate_jsonl(conflicts, require_core=False),
        validate_jsonl(rejected, require_core=False),
    ]
    all_valid = all(command["exit_code"] == 0 for command in commands) and all(item["valid"] for item in validations[:3])
    summary = {
        "valid": all_valid,
        "input_file": args.input_file,
        "input_sha256": sha256_file(REPO_ROOT / args.input_file),
        "alignment_model": args.alignment_model,
        "commands": commands,
        "outputs": validations,
        "promoted": bool(args.promote and all_valid),
    }
    (run_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_manifest(run_dir, validations)

    if not all_valid:
        return 1

    if args.promote:
        promote_pairs = [
            (mapped, REPO_ROOT / "data" / "interim" / "mapped_triples.jsonl"),
            (aligned, REPO_ROOT / "data" / "interim" / "aligned_triples.jsonl"),
            (fused, REPO_ROOT / "data" / "processed" / "fused_triples.jsonl"),
            (conflicts, REPO_ROOT / "data" / "interim" / "relation_conflicts.jsonl"),
            (rejected, REPO_ROOT / "data" / "interim" / "aggregation_rejected.jsonl"),
        ]
        for source, dest in promote_pairs:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
