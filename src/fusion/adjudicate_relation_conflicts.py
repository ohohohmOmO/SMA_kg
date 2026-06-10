import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evidence.context_builder import EvidenceContextBuilder
from src.evidence.loaders import count_jsonl_records, display_path, load_jsonl, sha256_file, write_json, write_jsonl
from src.extraction.llm_extractor import build_client, load_local_env


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
DECISION_CLASSES = {
    "supported_context_dependent",
    "extraction_error",
    "direction_error",
    "relation_normalization_issue",
    "real_conflict_needs_human_review",
    "insufficient_evidence",
}

SYSTEM_PROMPT = """
You are a biomedical relation-conflict adjudicator for an SMA knowledge graph.
Use ONLY the supplied Evidence Context. Do not use outside biomedical knowledge.

Return ONLY valid JSON with this shape:
{
  "decision": "supported_context_dependent",
  "retained_relations": ["RELATION"],
  "rejected_relations": ["RELATION"],
  "confidence": 0.0,
  "rationale": "brief evidence-grounded reason",
  "supporting_pmids": ["PMID"],
  "review_status": "adjudicated"
}

Allowed decision values:
supported_context_dependent, extraction_error, direction_error,
relation_normalization_issue, real_conflict_needs_human_review,
insufficient_evidence.

Rules:
1. Cite only PMIDs present in Evidence Context.
2. If evidence is missing or too weak, use insufficient_evidence.
3. If both polarities are supported in different contexts, use supported_context_dependent.
4. If one relation is unsupported by evidence text, use extraction_error.
5. If relation direction appears reversed, use direction_error.
6. If the conflict is caused by relation alias or polarity mapping, use relation_normalization_issue.
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Build and optionally adjudicate Stage 3 relation-conflict evidence contexts.")
    parser.add_argument("--conflicts-file", default="data/interim/relation_conflicts.jsonl")
    parser.add_argument("--abstracts-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--aligned-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--fused-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--dry-run", action="store_true", help="Write payloads only; do not call an LLM.")
    parser.add_argument("--limit", type=int, default=-1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=1024)
    return parser.parse_args()


def main():
    args = parse_args()
    load_local_env()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = (REPO_ROOT / args.run_dir).resolve() if args.run_dir else REPO_ROOT / "artifacts" / "runs" / f"conflict_adjudication_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    conflicts, bad_lines = load_jsonl(REPO_ROOT / args.conflicts_file)
    if bad_lines:
        write_json(run_dir / "validation_summary.json", {"valid": False, "bad_conflict_json_lines": len(bad_lines)})
        return 1
    selected = conflicts if args.limit < 0 else conflicts[: args.limit]

    builder = EvidenceContextBuilder(
        abstracts_file=REPO_ROOT / args.abstracts_file,
        aligned_triples_file=REPO_ROOT / args.aligned_file,
        fused_triples_file=REPO_ROOT / args.fused_file,
        conflicts_file=REPO_ROOT / args.conflicts_file,
    )
    payloads = []
    for idx, conflict in enumerate(selected, 1):
        context = builder.build_conflict_context(conflict, conflict_id=f"SMA-CONFLICT-{idx:04d}")
        payloads.append(build_payload(context, conflict, idx))

    payload_file = run_dir / "payloads.jsonl"
    write_jsonl(payload_file, payloads)

    adjudications = []
    unresolved = []
    failed = []
    live_mode = not args.dry_run
    if live_mode:
        api_key = os.environ.get("SILICONFLOW_API_KEY")
        if not api_key:
            write_json(run_dir / "validation_summary.json", {
                "valid": False,
                "mode": "live",
                "error": "SILICONFLOW_API_KEY is not set; use --dry-run for payload generation.",
                "payload_records": len(payloads),
            })
            write_manifest(run_dir, args, payload_file, None, None, None)
            return 1
        client = build_client(api_key)
        for payload in payloads:
            if not payload["evidence_context"].get("aligned_triples"):
                unresolved.append(insufficient_evidence_adjudication(payload))
                continue
            try:
                adjudication = adjudicate_with_llm(client, payload, args.model, args.max_tokens)
                problems = validate_adjudication(adjudication, payload)
                if problems:
                    failed.append({"payload": payload, "problems": problems, "raw_adjudication": adjudication})
                else:
                    adjudications.append(adjudication)
            except Exception as exc:
                failed.append({"payload": payload, "error": str(exc)})

    adjudication_file = run_dir / "adjudications.jsonl"
    unresolved_file = run_dir / "unresolved.jsonl"
    failed_file = run_dir / "rejected_or_failed.jsonl"
    if live_mode:
        write_jsonl(adjudication_file, adjudications)
        write_jsonl(unresolved_file, unresolved)
        write_jsonl(failed_file, failed)

    summary = {
        "valid": True if args.dry_run else len(failed) == 0,
        "mode": "dry_run" if args.dry_run else "live",
        "model": args.model if live_mode else "",
        "conflict_records_input": len(conflicts),
        "conflict_records_selected": len(selected),
        "payload_records": len(payloads),
        "adjudication_records": len(adjudications),
        "unresolved_records": len(unresolved),
        "failed_records": len(failed),
        "outputs": {
            "payloads": display_path(payload_file),
            "adjudications": display_path(adjudication_file) if adjudication_file.exists() else "",
            "unresolved": display_path(unresolved_file) if unresolved_file.exists() else "",
            "rejected_or_failed": display_path(failed_file) if failed_file.exists() else "",
        },
        "canonical_graph_mutated": False,
    }
    write_json(run_dir / "validation_summary.json", summary)
    write_manifest(
        run_dir,
        args,
        payload_file,
        adjudication_file if adjudication_file.exists() else None,
        unresolved_file if unresolved_file.exists() else None,
        failed_file if failed_file.exists() else None,
    )
    return 0 if summary["valid"] else 1


def build_payload(context, conflict, index):
    return {
        "conflict_id": context["context_id"],
        "conflict_index": index,
        "entity_1": conflict.get("entity_1", {}),
        "entity_2": conflict.get("entity_2", {}),
        "conflicting_relations": conflict.get("relations", []),
        "reason": conflict.get("reason", ""),
        "review_status": conflict.get("review_status", ""),
        "evidence_context": context,
    }


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(Exception),
)
def call_llm(client, payload, model, max_tokens):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def adjudicate_with_llm(client, payload, model, max_tokens):
    raw = call_llm(client, payload, model, max_tokens)
    data = json.loads(clean_json_text(raw))
    data["conflict_id"] = payload["conflict_id"]
    data["entity_1"] = payload["entity_1"]
    data["entity_2"] = payload["entity_2"]
    data["conflicting_relations"] = payload["conflicting_relations"]
    data["model"] = model
    data.setdefault("review_status", "adjudicated")
    return data


def clean_json_text(raw_text):
    cleaned = str(raw_text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def validate_adjudication(record, payload):
    problems = []
    if record.get("decision") not in DECISION_CLASSES:
        problems.append("decision_invalid")
    for key in ("retained_relations", "rejected_relations", "supporting_pmids"):
        if not isinstance(record.get(key), list):
            problems.append(f"{key}_not_list")
    try:
        confidence = float(record.get("confidence"))
        if confidence < 0 or confidence > 1:
            problems.append("confidence_out_of_range")
    except (TypeError, ValueError):
        problems.append("confidence_invalid")
    allowed_pmids = set(payload["evidence_context"].get("supporting_pmids", []))
    for pmid in record.get("supporting_pmids", []):
        if str(pmid) not in allowed_pmids:
            problems.append("supporting_pmid_not_in_context")
            break
    return problems


def insufficient_evidence_adjudication(payload):
    return {
        "conflict_id": payload["conflict_id"],
        "entity_1": payload["entity_1"],
        "entity_2": payload["entity_2"],
        "conflicting_relations": payload["conflicting_relations"],
        "decision": "insufficient_evidence",
        "retained_relations": [],
        "rejected_relations": [],
        "confidence": 0.0,
        "rationale": "No aligned evidence triples were retrieved for this conflict payload.",
        "supporting_pmids": [],
        "model": "",
        "review_status": "unresolved",
    }


def write_manifest(run_dir, args, payload_file, adjudication_file, unresolved_file, failed_file):
    rows = []
    for artifact, path, notes in [
        ("payloads", payload_file, "dry-run evidence contexts for conflict adjudication"),
        ("adjudications", adjudication_file, "live LLM adjudications"),
        ("unresolved", unresolved_file, "insufficient evidence or unresolved decisions"),
        ("rejected_or_failed", failed_file, "failed LLM calls or invalid adjudication JSON"),
        ("validation_summary", run_dir / "validation_summary.json", "run validation summary"),
    ]:
        if path is None or not Path(path).exists():
            continue
        path = Path(path)
        rows.append({
            "artifact": artifact,
            "path": display_path(path),
            "records": count_jsonl_records(path) if path.suffix == ".jsonl" else "",
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "notes": notes,
        })
    with (run_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "records", "bytes", "sha256", "notes"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
