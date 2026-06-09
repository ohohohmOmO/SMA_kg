import argparse
import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.confidence import normalize_and_score


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


DRUGS = {
    "nusinersen": "Nusinersen",
    "spinraza": "Nusinersen",
    "risdiplam": "Risdiplam",
    "evrysdi": "Risdiplam",
    "zolgensma": "Onasemnogene Abeparvovec",
    "onasemnogene abeparvovec": "Onasemnogene Abeparvovec",
}
GENES = {
    "smn1": "SMN1",
    "smn2": "SMN2",
    "smn": "SMN",
}
DISEASES = {
    "spinal muscular atrophy": "Spinal Muscular Atrophy",
    "sma": "Spinal Muscular Atrophy",
}
PHENOTYPES = {
    "motor function": "motor function",
    "motor milestone": "motor milestones",
    "motor milestones": "motor milestones",
    "muscle weakness": "muscle weakness",
    "survival": "survival",
    "respiratory": "respiratory function",
}

TREAT_CUE = re.compile(r"\b(treat|therapy|therapeutic|administer|receive|approved|dose|treatment)\w*\b", re.I)
IMPROVE_CUE = re.compile(r"\b(improv|benefit|increase|gain|restore|rescue|stabili[sz]e|preserve)\w*\b", re.I)
ASSOC_CUE = re.compile(r"\b(associat|linked|correlat|variant|mutation|deletion|copy number|cause)\w*\b", re.I)
NEGATION_CUE = re.compile(r"\b(no|not|without|lack|lacks|failed to|did not|does not|no significant)\b", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def contains_term(sentence_lower, term):
    pattern = r"(?<![A-Za-z0-9])" + re.escape(term.lower()) + r"(?![A-Za-z0-9])"
    return re.search(pattern, sentence_lower) is not None


def sentence_has_negated_relation(sentence):
    return NEGATION_CUE.search(sentence) is not None


def iter_sentences(text):
    for sentence in SENTENCE_SPLIT.split(str(text or "")):
        sentence = re.sub(r"\s+", " ", sentence).strip()
        if sentence:
            yield sentence


def add_validated(triples, raw):
    normalized, problems = normalize_and_score(raw, require_evidence=True)
    if problems:
        return problems
    triples.append(normalized)
    return []


def rule_candidate_extraction(text, pmid, include_rejections=False):
    triples = []
    rejected = []

    for sentence in iter_sentences(text):
        sentence_lower = sentence.lower()
        if sentence_has_negated_relation(sentence):
            continue

        present_diseases = [canonical for term, canonical in DISEASES.items() if contains_term(sentence_lower, term)]
        present_drugs = [(term, canonical) for term, canonical in DRUGS.items() if contains_term(sentence_lower, term)]
        present_genes = [(term, canonical) for term, canonical in GENES.items() if contains_term(sentence_lower, term)]
        present_phenotypes = [
            (term, canonical) for term, canonical in PHENOTYPES.items() if contains_term(sentence_lower, term)
        ]

        if present_drugs and present_diseases and TREAT_CUE.search(sentence):
            for _, drug in present_drugs:
                raw = {
                    "source_pmid": pmid,
                    "entity_1": {"name": drug, "type": "Drug"},
                    "relation": "TREATS",
                    "entity_2": {"name": present_diseases[0], "type": "Disease"},
                    "evidence_text": sentence,
                    "extracted_by": "Rule_Candidate",
                }
                problems = add_validated(triples, raw)
                if problems:
                    rejected.append({"problems": problems, "record": raw})

        if present_drugs and present_phenotypes and IMPROVE_CUE.search(sentence):
            for _, drug in present_drugs:
                for _, phenotype in present_phenotypes:
                    raw = {
                        "source_pmid": pmid,
                        "entity_1": {"name": drug, "type": "Drug"},
                        "relation": "IMPROVES",
                        "entity_2": {"name": phenotype, "type": "Phenotype"},
                        "evidence_text": sentence,
                        "extracted_by": "Rule_Candidate",
                    }
                    problems = add_validated(triples, raw)
                    if problems:
                        rejected.append({"problems": problems, "record": raw})

        if present_genes and present_diseases and ASSOC_CUE.search(sentence):
            for _, gene in present_genes:
                raw = {
                    "source_pmid": pmid,
                    "entity_1": {"name": gene, "type": "Gene"},
                    "relation": "ASSOCIATED_WITH",
                    "entity_2": {"name": present_diseases[0], "type": "Disease"},
                    "evidence_text": sentence,
                    "extracted_by": "Rule_Candidate",
                }
                problems = add_validated(triples, raw)
                if problems:
                    rejected.append({"problems": problems, "record": raw})

    if include_rejections:
        return triples, rejected
    return triples


regex_fallback_extraction = rule_candidate_extraction


def parse_args():
    parser = argparse.ArgumentParser(description="Run sentence-level local rule candidate extraction.")
    parser.add_argument("--input-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--output-file", default="data/interim/rule_candidate_triples.jsonl")
    parser.add_argument("--rejected-file", default="data/interim/rule_candidate_triples.rejected.jsonl")
    parser.add_argument("--offset", type=int, default=200)
    parser.add_argument("--limit", type=int, default=-1)
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    rejected_file = Path(args.rejected_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    rejected_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        logging.error("Input file %s not found.", input_file)
        return 1

    stop = None if args.limit < 0 else args.offset + args.limit
    df = pd.read_json(input_file, lines=True).iloc[args.offset:stop]

    successful_triples = 0
    rejected_triples = 0
    with output_file.open("w", encoding="utf-8") as f, rejected_file.open("w", encoding="utf-8") as rejected:
        for _, row in df.iterrows():
            pmid = str(row.get("pmid", ""))
            abstract = row.get("abstract", "")
            if not abstract:
                continue

            triples, rejected_items = rule_candidate_extraction(abstract, pmid, include_rejections=True)
            seen = set()
            for triple in triples:
                sig = (
                    triple["entity_1"]["name"],
                    triple["relation"],
                    triple["entity_2"]["name"],
                    triple.get("evidence_text", ""),
                )
                if sig in seen:
                    continue
                seen.add(sig)
                f.write(json.dumps(triple, ensure_ascii=False) + "\n")
                successful_triples += 1
            for item in rejected_items:
                rejected.write(json.dumps(item, ensure_ascii=False) + "\n")
                rejected_triples += 1

    logging.info("Local rule candidate extraction complete. Extracted %s candidates to %s.", successful_triples, output_file)
    logging.info("Rejected %s local rule triples to %s.", rejected_triples, rejected_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
