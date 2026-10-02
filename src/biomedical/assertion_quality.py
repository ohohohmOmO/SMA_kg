"""Conservative context/type triage, retaining unchanged predictions and source text.

This is an error screen, not a semantic entailment or medical correctness test.
"""
import re
from src.biomedical.evidence_validation import validate_evidence, source_sentences, normalized_text

VERSION = "assertion_context_type_v1"
CONTEXT_PATTERNS = {
    "population_or_stage": r"\b(?:patients?|infants?|adults?|children|pediatric|neonatal|presymptomatic|symptomatic|type\s*(?:[0-4]|i{1,3}|iv))\b",
    "experimental_model": r"\b(?:mice|mouse|murine|rat|rats|in vitro|in vivo|cell lines?|animal|models?)\b",
    "conditional_or_comparative": r"\b(?:if|when|only|unless|depending|compared|versus|relative to|whereas|after|before|following|in patients|in children|with deletion|deficien\w*|loss|knockdown|mutat\w*|delet\w*|copies|copy number)\b",
    "negation_or_modality": r"\b(?:not|no|without|failed|may|might|could|potential|suggest\w*|hypothes\w*)\b",
}
EXPECTED_TYPES = {
    "nusinersen": "Drug", "spinraza": "Drug", "risdiplam": "Drug", "evrysdi": "Drug",
    "onasemnogene abeparvovec": "Drug", "zolgensma": "Drug",
    "spinal muscular atrophy": "Disease", "sma": "Disease",
    "motor function": "Phenotype", "muscle weakness": "Phenotype",
}


def type_flags(entity):
    name, etype = normalized_text(entity.get("name", "")), entity.get("type", "")
    expected = EXPECTED_TYPES.get(name)
    if expected and etype != expected:
        return ["known_name_type_mismatch"]
    if re.search(r"\b(?:protein|proteins)\b", name) and etype == "Gene":
        return ["protein_named_as_gene"]
    if etype == "Gene" and re.search(r"\b(?:deletion|mutation|variant|allele|exon|copy number|copies)\b", name):
        return ["gene_part_or_variant_named_as_whole_gene"]
    if etype == "Gene" and name in {"smn", "smn1", "smn2"}:
        # Bare gene symbols are also used to refer to proteins in abstracts.
        return ["gene_symbol_context_requires_review"]
    if etype in {"Gene", "Protein"} and re.search(r"\b(?:patients?|children|infants?|adults?)\b", name):
        return ["population_named_as_molecular_entity"]
    if re.search(r"(?:^sma\s*type|^spinal muscular atrophy\s*type)", name) and etype != "Disease":
        return ["disease_subtype_type_requires_review"]
    return []


def screen_assertion(record, source, dictionary=None, suggest_fuzzy=False):
    location = validate_evidence(record, source, dictionary, suggest_fuzzy=suggest_fuzzy)
    flags = list(location["flags"])
    contexts, seen = [], set()
    for segment in location["segments"]:
        text = str((source or {}).get(segment["field"], ""))
        for a, b, sentence in source_sentences(text):
            if a < segment["end"] and b > segment["start"] and (segment["field"], a, b) not in seen:
                seen.add((segment["field"], a, b))
                contexts.append({"field": segment["field"], "start": a, "end": b, "text": sentence,
                                 "scope_cues": [key for key, pattern in CONTEXT_PATTERNS.items() if re.search(pattern, sentence, re.I)]})
    for key in ("entity_1", "entity_2"):
        flags.extend(key + ":" + flag for flag in type_flags(record[key]))
    if any(x["scope_cues"] for x in contexts):
        flags.append("qualified_statement_requires_review")
    if any(re.search(r"\b(?:loss|deficien\w*|knockdown|delet\w*|mutat\w*)\b", x["text"], re.I) for x in contexts) and record["relation"] == "CAUSES" and record["entity_1"]["type"] in {"Gene", "Protein"}:
        flags.append("gene_perturbation_is_not_gene_itself")
    flags = sorted(set(flags))
    return {"version": VERSION, "location": location, "context_sentences": contexts,
            "flags": flags, "eligible_candidate": location["eligible_span"] and not flags,
            "semantic_support": "not_evaluated", "review_status": "needs_review" if flags else "screened_candidate",
            "original_assertion_preserved": True}
