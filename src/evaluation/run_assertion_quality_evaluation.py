"""Frozen, label-blind assertion screening experiment against unchanged human labels."""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.biomedical.assertion_quality import VERSION, screen_assertion
from src.biomedical.evidence_validation import source_sentences
from src.evaluation.audit_fyp_inputs import load_jsonl, DEFAULT_CANDIDATES
from src.evaluation.fyp_dataset import candidate_record, classify_gate, pmid_split, read_review_dataset, sha256, cluster_interval
from src.extraction.llm_extractor import build_client, load_local_env
from src.fusion.dictionary_mapper import load_dictionary

VERIFIER_PROMPT = """Evaluate the ORIGINAL directed biomedical assertion using ONLY the provided title/abstract. No world knowledge or inferred therapeutic plausibility. Do not rewrite the assertion.
Return JSON with support ('direct','partial','unsupported','unclear'), entity_types_correct (boolean), direction_correct (boolean), conditions_preserved (boolean), evidence_quote (one or more complete contiguous original sentences, verbatim), source_field ('title' or 'abstract'), missing_conditions (list of strings), reason (string).
Direct means BOTH typed endpoints AND the directed relation are explicitly supported with their original scope. A correct relation with a wrong entity type is NOT direct. Gene and protein are distinct. Gene deletion/deficiency/mutation causing disease does NOT justify the bare gene CAUSES disease. A generic gene symbol used for protein requires local disambiguation. Association does NOT imply causation. Splicing, expression, copy number, and mutant alleles are NOT automatically equivalent to the bare gene. Compare populations, clinical subtype, age/stage, dosage/time, comparator, experimental species/model, negation and uncertainty. If the unqualified assertion drops a material condition or upgrades possibility/comparison to unconditional fact, set conditions_preserved=false and support=partial or unsupported.
Evidence must retain the predicate, both entities or source-resolved references, and necessary conditions. Quote only existing text; never fabricate/repair a quote. If no full supporting quote exists, use evidence_quote='' and support=unsupported or unclear. Preserve ambiguity rather than guessing. Return only JSON."""


def validate_model_decision(decision, source):
    problems = []
    if decision.get("support") not in {"direct", "partial", "unsupported", "unclear"}:
        problems.append("invalid_support")
    for key in ("entity_types_correct", "direction_correct", "conditions_preserved"):
        if type(decision.get(key)) is not bool:
            problems.append("invalid_" + key)
    field = decision.get("source_field")
    quote = decision.get("evidence_quote", "")
    if field not in {"title", "abstract"} or not isinstance(quote, str):
        problems.append("invalid_quote_schema")
    elif quote and quote not in str(source.get(field, "")):
        problems.append("quote_not_in_source")
    elif quote:
        text = str(source.get(field, ""))
        start = text.index(quote)
        end = start + len(quote)
        sentences = [(a, b, s) for a, b, s in source_sentences(text) if a < end and b > start]
        if field == "title":
            complete = quote.strip() == text.strip()
        else:
            complete = bool(sentences) and text[sentences[0][0]:sentences[-1][1]].strip() == quote.strip()
        if not complete:
            problems.append("quote_incomplete_sentence")
    if not isinstance(decision.get("missing_conditions"), list) or not isinstance(decision.get("reason"), str):
        problems.append("invalid_rationale_schema")
    accepted = not problems and bool(quote) and not decision.get("missing_conditions") and decision.get("support") == "direct" and all(
        decision.get(key) is True for key in ("entity_types_correct", "direction_correct", "conditions_preserved"))
    return {"schema_errors": problems, "model_screened_candidate": accepted,
            "verification_origin": "LLM_assisted_not_human", "independent_human_confirmation": False}


def run_model(client, request, model):
    for _ in range(2):
        try:
            response = client.chat.completions.create(model=model, temperature=0,
                max_tokens=1400, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": VERIFIER_PROMPT},
                          {"role": "user", "content": json.dumps(request["payload"], ensure_ascii=False)}])
            decision = json.loads(response.choices[0].message.content)
            return {"candidate_id": request["candidate_id"], "decision": decision,
                    "validation": validate_model_decision(decision, request["payload"]["source"]),
                    "usage": response.usage.model_dump() if response.usage else None,
                    "error": None}
        except Exception as exc:
            error = type(exc).__name__
    return {"candidate_id": request["candidate_id"], "decision": None,
            "validation": {"model_screened_candidate": False}, "error": error}


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--with-llm", action="store_true")
    parser.add_argument("--replay-model-dir", help="Revalidate preserved model decisions after a documented implementation correction; no API calls")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V4-Flash")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.with_llm and args.replay_model_dir:
        parser.error("Use either new API calls or preserved-decision replay")
    model_evaluated = bool(args.with_llm or args.replay_model_dir)
    out = ROOT / args.run_dir
    out.mkdir(parents=True, exist_ok=False)
    workbook = ROOT / args.workbook
    rows, checks = read_review_dataset(workbook, ROOT / DEFAULT_CANDIDATES)
    sources, errors = load_jsonl(ROOT / "data/raw/pubmed_sma_abstracts.jsonl")
    raw, raw_errors = load_jsonl(ROOT / "data/processed/extracted_triples.jsonl")
    assert not errors and not raw_errors
    sources = {str(r["pmid"]): r for r in sources}
    dictionary = load_dictionary(ROOT / "resources/entity_dictionary.json")
    inputs = {"workbook": workbook, "raw": ROOT / "data/processed/extracted_triples.jsonl",
              "abstracts": ROOT / "data/raw/pubmed_sma_abstracts.jsonl", "candidates": ROOT / DEFAULT_CANDIDATES,
              "dictionary": ROOT / "resources/entity_dictionary.json", "screen_code": ROOT / "src/biomedical/assertion_quality.py",
              "runner_code": Path(__file__).resolve()}
    hashes = {key: sha256(path) for key, path in inputs.items()}
    # Written BEFORE screening/API requests; no rule or threshold tuning after outcomes.
    dump(out / "frozen_protocol.json", {"version": VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
         "args": vars(args), "input_sha256": hashes, "verifier_prompt": VERIFIER_PROMPT,
         "verifier_prompt_sha256": hashlib.sha256(VERIFIER_PROMPT.encode()).hexdigest(),
         "evaluation_design": "retrospective internal paired screening, previously inspected labels; no independent prospective test",
         "primary_endpoint": "strict support among retained ORIGINAL predictions; retention and strict-positive loss reported",
         "human_label_transfer_to_rewrites": False, "automatic_rewrite_or_delete": False,
         "api_receives_human_labels_or_notes": False, "dataset_checks": checks})
    corpus_counts, corpus_flags = Counter(), Counter()
    with (out / "assertion_quality_full.jsonl").open("w", encoding="utf-8") as stream:
        for i, record in enumerate(raw, 1):
            quality = screen_assertion(record, sources[str(record["source_pmid"])], dictionary)
            corpus_counts[quality["review_status"]] += 1; corpus_flags.update(quality["flags"])
            stream.write(json.dumps({"raw_record_number": i, "source_pmid": record["source_pmid"],
                                     "original_assertion": record, "quality": quality}, ensure_ascii=False) + "\n")
    requests, results = [], []
    for row in rows:
        record = candidate_record(row)
        source = {key: row[key] for key in ("title", "abstract")}
        quality = screen_assertion(record, source, dictionary)
        results.append({"candidate_id": row["candidate_id"], "quality": quality})
        requests.append({"candidate_id": row["candidate_id"], "payload": {"assertion": record, "source": source}})
    write_jsonl(out / "label_blind_requests.jsonl", requests)
    decisions = []
    if args.replay_model_dir:
        previous = ROOT / args.replay_model_dir
        assert sha256(previous / "label_blind_requests.jsonl") == sha256(out / "label_blind_requests.jsonl"), "Replay requests differ"
        decisions, replay_errors = load_jsonl(previous / "model_decisions.jsonl")
        assert not replay_errors and len(decisions) == len(requests)
        assert len({d["candidate_id"] for d in decisions}) == len(requests)
        request_index = {r["candidate_id"]: r for r in requests}
        for decision in decisions:
            if decision.get("decision") is not None:
                decision["validation"] = validate_model_decision(decision["decision"], request_index[decision["candidate_id"]]["payload"]["source"])
        write_jsonl(out / "model_decisions.jsonl", decisions)
        dump(out / "replay_provenance.json", {"reason": "Correct decimal punctuation truncating original source sentence context; no prompt, model response, label or threshold changes",
            "source_run": str(previous), "source_decisions_sha256": sha256(previous / "model_decisions.jsonl"), "new_api_calls": 0,
            "sentence_code_sha256": sha256(ROOT / "src/biomedical/evidence_validation.py")})
    if args.with_llm:
        load_local_env()
        if not os.getenv("SILICONFLOW_API_KEY"):
            raise RuntimeError("SILICONFLOW_API_KEY missing; protocol and source artifacts retained")
        client = build_client(os.environ["SILICONFLOW_API_KEY"])
        with (out / "model_decisions.jsonl").open("w", encoding="utf-8") as stream, ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [pool.submit(run_model, client, request, args.model) for request in requests]
            for job in as_completed(jobs):
                result = job.result(); decisions.append(result)
                stream.write(json.dumps(result, ensure_ascii=False) + "\n"); stream.flush()
                if len(decisions) % 40 == 0:
                    print(f"Model screening {len(decisions)}/{len(requests)}", flush=True)
        client.close()
    decision_index = {r["candidate_id"]: r for r in decisions}
    split = pmid_split(rows)
    gates = {"all_predictions": {}, "previous_evidence_triage": {}, "context_type_screen": {}, "model_direct_screen": {}, "combined_screen": {}}
    for result in results:
        cid, q = result["candidate_id"], result["quality"]
        model_ok = decision_index.get(cid, {}).get("validation", {}).get("model_screened_candidate", False)
        gates["all_predictions"][cid] = True
        gates["previous_evidence_triage"][cid] = q["location"]["eligible_span"]
        gates["context_type_screen"][cid] = q["eligible_candidate"]
        gates["model_direct_screen"][cid] = model_ok
        # The LLM handles explicit qualification while the original evidence gate
        # preserves the unchanged original-span evaluation denominator.
        gates["combined_screen"][cid] = model_ok and q["location"]["eligible_span"]
        result.update({"split": split[cid], "model": decision_index.get(cid), "gates": {key: values[cid] for key, values in gates.items()}})
    write_jsonl(out / "candidate_quality_results.jsonl", results)
    metrics = {}
    for group in ("primary_random", "challenge"):
        for subset in ("all", "development", "test"):
            selected = [r for r in rows if r["sample_group"] == group and (subset == "all" or split[r["candidate_id"]] == subset)]
            metrics[group + ":" + subset] = {}
            for key, predictions in gates.items():
                if key.startswith("model") or key == "combined_screen":
                    if not model_evaluated: continue
                retained = [r for r in selected if predictions[r["candidate_id"]]]
                measured = classify_gate(selected, predictions)
                measured["pmid_cluster_bootstrap_95_strict_retained"] = cluster_interval(retained, lambda r: r["support_label"] == "2")
                measured["strict_false_accepts"] = sum(r["support_label"] != "2" for r in retained)
                measured["strict_positive_loss"] = measured["strict_supported_candidates_total"] - measured["strict_supported_candidates_retained"]
                metrics[group + ":" + subset][key] = measured
    summary = {"metrics": metrics, "corpus_triage_counts": dict(corpus_counts), "corpus_flags": dict(corpus_flags),
               "model_requests": len(decisions), "model_failures": sum(bool(r["error"]) for r in decisions),
               "model_schema_failures": sum(bool(r.get("validation", {}).get("schema_errors")) for r in decisions),
               "ground_truth": "400 user-confirmed human labels of unchanged original predictions",
               "semantic_verifier": "LLM-assisted classification; not independent human evaluation of rewritten triples",
               "pmid_overlap": 0, "human_source_workbook_unchanged": sha256(workbook) == hashes["workbook"],
               "error_categories": {g: dict(Counter(r.get("error_type") or "not_recorded" for r in rows if r["sample_group"] == g)) for g in ("primary_random", "challenge")}}
    assert all(sha256(path) == hashes[key] for key, path in inputs.items())
    dump(out / "validation_summary.json", summary)
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["role", "path", "sha256"]); writer.writeheader()
        writer.writerows({"role": key, "path": str(path), "sha256": hashes[key]} for key, path in inputs.items())
    print(json.dumps({"main_test": metrics["primary_random:test"], "model_failures": summary["model_failures"], "corpus": summary["corpus_triage_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
