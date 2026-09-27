import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.schema import normalize_relation, relation_polarity
from src.evidence.loaders import load_jsonl
from src.qa.claim_evidence_validation import validate_claim_evidence


RELATION_VERBS = {
    "TREATS": "treats",
    "IMPROVES": "improves",
    "WORSENS": "worsens",
    "CAUSES": "causes",
    "DECREASES": "decreases",
    "INCREASES": "increases",
    "PREVENTS": "prevents",
    "DIAGNOSES": "diagnoses",
    "HAS_PHENOTYPE": "has",
    "ASSOCIATED_WITH": "is associated with",
}

POLARITY_FLIPS = {
    "TREATS": "worsens",
    "IMPROVES": "worsens",
    "WORSENS": "improves",
    "CAUSES": "prevents",
    "DECREASES": "increases",
    "INCREASES": "decreases",
    "PREVENTS": "causes",
}

POPULATION_SWAPS = {
    "infant": "adults",
    "infants": "adults",
    "child": "adults",
    "children": "adults",
    "pediatric": "adults",
    "paediatric": "adults",
    "adult": "infants",
    "adults": "infants",
    "elderly": "infants",
}


def build_silver_cases(records, limit=200):
    usable = [
        record
        for record in records
        if str(record.get("evidence_text", "")).strip()
        and record.get("entity_1", {}).get("name")
        and record.get("entity_2", {}).get("name")
        and normalize_relation(record.get("relation", "")) in RELATION_VERBS
    ][: max(0, int(limit))]
    cases = []
    for index, source in enumerate(usable, 1):
        evidence = {
            **source,
            "evidence_id": f"S{index:05d}",
            "source_pmid": str(source.get("source_pmid", "")),
        }
        relation = normalize_relation(evidence.get("relation", ""))
        entity_1 = str(evidence["entity_1"]["name"])
        entity_2 = str(evidence["entity_2"]["name"])
        verb = RELATION_VERBS[relation]
        base_text = f"{entity_1} {verb} {entity_2}."
        claim_type = _claim_type_for_relation(relation)
        cases.append(
            _case(index, "triple_positive", "entailed", base_text, claim_type, evidence)
        )

        if relation_polarity(relation) == "positive":
            negated = f"{entity_1} does not {verb.rstrip('s')} {entity_2}."
            cases.append(
                _case(
                    index,
                    "negation_flip",
                    "contradicted",
                    negated,
                    claim_type,
                    evidence,
                )
            )
        if relation in POLARITY_FLIPS:
            flipped = f"{entity_1} {POLARITY_FLIPS[relation]} {entity_2}."
            cases.append(
                _case(
                    index,
                    "relation_polarity_flip",
                    "contradicted",
                    flipped,
                    claim_type,
                    evidence,
                )
            )

        numeric = re.search(r"\b(\d+(?:\.\d+)?)\s*(mg|g|mcg|µg|ml)\b", evidence["evidence_text"], re.I)
        if numeric:
            changed = float(numeric.group(1)) + 1
            changed_text = str(int(changed)) if changed.is_integer() else str(changed)
            dosage_claim = (
                f"{entity_1} {verb} {entity_2} at {changed_text} {numeric.group(2)}."
            )
            cases.append(
                _case(
                    index,
                    "numeric_change",
                    "contradicted",
                    dosage_claim,
                    "dosage",
                    evidence,
                )
            )

        population = _first_population(evidence["evidence_text"])
        if population:
            population_claim = (
                f"{entity_1} {verb} {entity_2} in {POPULATION_SWAPS[population]}."
            )
            cases.append(
                _case(
                    index,
                    "population_change",
                    "insufficient",
                    population_claim,
                    claim_type,
                    evidence,
                )
            )

        cases.append(
            _case(
                index,
                "unrelated_entities",
                "unrelated",
                "ZZZ unrelated intervention diagnoses ZZZ unrelated outcome.",
                "diagnosis",
                evidence,
            )
        )
    return cases


def evaluate_silver_cases(cases):
    confusion = Counter()
    mismatched = []
    for case in cases:
        evidence = case["evidence"]
        context = {
            "aligned_triples": [evidence],
            "fused_edges": [],
            "graph_neighborhood": [],
            "allowed_evidence_ids": [evidence["evidence_id"]],
            "allowed_citation_pmids": [str(evidence.get("source_pmid", ""))],
        }
        result = validate_claim_evidence(case["claim"], context)
        expected = case["expected_label"]
        predicted = result["label"]
        confusion[(expected, predicted)] += 1
        if expected != predicted:
            mismatched.append(
                {
                    "case_id": case["case_id"],
                    "expected": expected,
                    "predicted": predicted,
                    "violations": result["violations"],
                }
            )
    total = len(cases)
    matches = total - len(mismatched)
    return {
        "total": total,
        "matches": matches,
        "mismatches": len(mismatched),
        "accuracy": matches / total if total else 0.0,
        "confusion": {
            f"{expected}->{predicted}": count
            for (expected, predicted), count in sorted(confusion.items())
        },
        "mismatch_examples": mismatched[:50],
        "gold_standard": False,
        "evaluation_scope": "weakly_supervised_silver_regression",
    }


def _case(index, method, expected, text, claim_type, evidence):
    return {
        "case_id": f"CE{index:05d}-{method}",
        "generation_method": method,
        "expected_label": expected,
        "claim": {
            "claim_id": f"C{index:05d}",
            "claim_type": claim_type,
            "text": text,
            "supporting_pmids": [str(evidence.get("source_pmid", ""))],
            "supporting_evidence_ids": [evidence["evidence_id"]],
        },
        "evidence": evidence,
        "is_human_labeled": False,
    }


def _claim_type_for_relation(relation):
    if relation in {"TREATS", "IMPROVES", "WORSENS", "PREVENTS"}:
        return "treatment"
    if relation == "DIAGNOSES":
        return "diagnosis"
    return "association"


def _first_population(text):
    lowered = str(text).lower()
    for term in POPULATION_SWAPS:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            return term
    return ""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build and evaluate a weakly supervised claim-evidence silver set."
    )
    parser.add_argument("--input-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--limit", type=int, default=200)
    return parser.parse_args()


def main():
    args = parse_args()
    records, bad_lines = load_jsonl(args.input_file)
    if bad_lines:
        raise ValueError(f"Input contains {bad_lines} invalid JSON lines.")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = (
        (REPO_ROOT / args.run_dir).resolve()
        if args.run_dir
        else REPO_ROOT / "results" / "runs" / f"claim_evidence_silver_{stamp}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = build_silver_cases(records, limit=args.limit)
    summary = evaluate_silver_cases(cases)
    cases_file = run_dir / "silver_cases.jsonl"
    summary_file = run_dir / "validation_summary.json"
    with cases_file.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (run_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["artifact", "path", "records", "notes"])
        writer.writerow(
            [
                "silver_cases",
                str(cases_file.relative_to(REPO_ROOT)),
                len(cases),
                "automatically generated; not human gold labels",
            ]
        )
        writer.writerow(
            [
                "validation_summary",
                str(summary_file.relative_to(REPO_ROOT)),
                1,
                "deterministic weak-supervision regression result",
            ]
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["mismatches"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
