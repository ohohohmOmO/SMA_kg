import argparse
import json
import logging
import os
import sys
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from llm_extractor import build_client, load_local_env
except ModuleNotFoundError:
    from src.extraction.llm_extractor import build_client, load_local_env
from src.biomedical.confidence import normalize_and_score


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"

SYSTEM_PROMPT = """
You are a biomedical relation verification engine for SMA literature.
Verify whether one proposed relation triple is directly supported by the supplied PubMed abstract.

Return ONLY valid JSON with this exact shape:
{
  "supported": true,
  "confidence": 0.0,
  "evidence_text": "short supporting span copied or closely matched from the abstract",
  "reason": "brief reason"
}

Rules:
1. Use only the supplied abstract and candidate evidence, not biomedical background knowledge.
2. Mark supported=true only when the same relation direction and meaning are explicitly stated.
3. Co-occurrence or vague mention is not enough for causal, treatment, improvement, worsening, or regulatory relations.
4. If unsupported, set supported=false and confidence below 0.5.
5. evidence_text must be non-empty when supported=true.
"""


def load_jsonl(path):
    records = []
    bad_lines = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                bad_lines.append({"line": line_no, "error": str(exc), "raw": line[:500]})
    return records, bad_lines


def load_abstracts(path):
    records, bad_lines = load_jsonl(path)
    if bad_lines:
        raise ValueError(f"Abstract file has {len(bad_lines)} invalid JSON lines: {path}")
    abstracts = {}
    for record in records:
        pmid = str(record.get("pmid", "")).strip()
        if not pmid:
            continue
        title = str(record.get("title", "")).strip()
        abstract = str(record.get("abstract", "")).strip()
        abstracts[pmid] = f"Title: {title}\nAbstract: {abstract}".strip()
    return abstracts


def parse_verdict(raw_text):
    cleaned = str(raw_text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    verdict = json.loads(cleaned.strip())
    supported = bool(verdict.get("supported"))
    confidence = verdict.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "supported": supported,
        "confidence": confidence,
        "evidence_text": str(verdict.get("evidence_text", "")).strip(),
        "reason": str(verdict.get("reason", "")).strip(),
    }


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(Exception),
)
def call_verifier(client, candidate, abstract_text, model, max_tokens):
    payload = {
        "candidate_triple": {
            "source_pmid": candidate.get("source_pmid"),
            "entity_1": candidate.get("entity_1"),
            "relation": candidate.get("relation"),
            "entity_2": candidate.get("entity_2"),
            "candidate_evidence_text": candidate.get("evidence_text", ""),
        },
        "abstract": abstract_text,
    }
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


def verify_candidate(client, candidate, abstract_text, model, max_tokens, min_confidence):
    raw_verdict = call_verifier(client, candidate, abstract_text, model, max_tokens)
    verdict = parse_verdict(raw_verdict)
    if not verdict["supported"] or verdict["confidence"] < min_confidence:
        return None, {"kind": "unsupported", "verdict": verdict, "record": candidate}
    if not verdict["evidence_text"]:
        return None, {"kind": "missing_verified_evidence", "verdict": verdict, "record": candidate}

    verified = dict(candidate)
    verified["evidence_text"] = verdict["evidence_text"]
    verified["llm_confidence"] = verdict["confidence"]
    verified["extracted_by"] = f"LLM_Verified_RuleCandidate_{model}"
    verified["verification"] = {
        "verifier_model": model,
        "original_extracted_by": candidate.get("extracted_by", ""),
        "supported": verdict["supported"],
        "confidence": verdict["confidence"],
        "reason": verdict["reason"],
    }
    normalized, problems = normalize_and_score(verified, require_evidence=True)
    if problems:
        return None, {"kind": "schema_invalid_after_verification", "problems": problems, "record": verified}
    return normalized, None


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Use an LLM to verify local rule candidate triples. This writes an "
            "auxiliary verified-rule file and does not promote to canonical output."
        )
    )
    parser.add_argument("--input-file", default="data/interim/rule_candidate_triples.jsonl")
    parser.add_argument("--abstracts-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--output-file", default="data/interim/verified_rule_triples.jsonl")
    parser.add_argument("--rejected-file", default="data/interim/verified_rule_triples.rejected.jsonl")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=-1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    load_local_env()
    args = parse_args()
    input_file = Path(args.input_file)
    abstracts_file = Path(args.abstracts_file)
    output_file = Path(args.output_file)
    rejected_file = Path(args.rejected_file)

    if not input_file.exists():
        logging.error("Input file %s not found.", input_file)
        return 1
    if not abstracts_file.exists():
        logging.error("Abstracts file %s not found.", abstracts_file)
        return 1

    candidates, bad_lines = load_jsonl(input_file)
    if bad_lines:
        rejected_file.parent.mkdir(parents=True, exist_ok=True)
        with rejected_file.open("w", encoding="utf-8") as rejected:
            for item in bad_lines:
                rejected.write(json.dumps({"kind": "bad_json", **item}, ensure_ascii=False) + "\n")
        logging.error("Input file has %s invalid JSON lines.", len(bad_lines))
        return 1

    stop = None if args.limit < 0 else args.offset + args.limit
    selected = candidates[args.offset:stop]
    abstracts = load_abstracts(abstracts_file)
    missing_pmids = [item.get("source_pmid") for item in selected if str(item.get("source_pmid", "")) not in abstracts]

    if args.dry_run:
        logging.info(
            "Dry run: candidates=%s selected=%s missing_abstracts=%s output=%s",
            len(candidates),
            len(selected),
            len(missing_pmids),
            output_file,
        )
        return 0

    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        logging.error("SILICONFLOW_API_KEY is not set. Refusing to run rule candidate verification.")
        return 1

    client = build_client(api_key)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    rejected_file.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_file.with_name(f"{output_file.name}.tmp")
    temp_rejected = rejected_file.with_name(f"{rejected_file.name}.tmp")

    accepted_count = 0
    rejected_count = 0
    with temp_output.open("w", encoding="utf-8") as out, temp_rejected.open("w", encoding="utf-8") as rejected:
        for candidate in selected:
            pmid = str(candidate.get("source_pmid", "")).strip()
            abstract_text = abstracts.get(pmid)
            if not abstract_text:
                rejected.write(json.dumps({"kind": "missing_abstract", "record": candidate}, ensure_ascii=False) + "\n")
                rejected_count += 1
                continue
            try:
                verified, rejection = verify_candidate(
                    client,
                    candidate,
                    abstract_text,
                    args.model,
                    args.max_tokens,
                    args.min_confidence,
                )
            except Exception as exc:
                rejection = {"kind": "verification_error", "error": str(exc), "record": candidate}
                verified = None

            if verified:
                out.write(json.dumps(verified, ensure_ascii=False) + "\n")
                accepted_count += 1
            else:
                rejected.write(json.dumps(rejection, ensure_ascii=False) + "\n")
                rejected_count += 1

    temp_output.replace(output_file)
    temp_rejected.replace(rejected_file)
    logging.info(
        "Rule candidate verification complete. accepted=%s rejected=%s output=%s rejected_file=%s",
        accepted_count,
        rejected_count,
        output_file,
        rejected_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
