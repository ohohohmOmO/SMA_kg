import re

from src.biomedical.schema import normalize_relation, relation_polarity


CRITICAL_CLAIM_TYPES = {
    "diagnosis",
    "treatment",
    "dosage",
    "contraindication",
    "safety",
}

RELATION_TERMS = {
    "TREATS": ("treat", "treats", "treated", "therapy"),
    "IMPROVES": ("improve", "improves", "improved", "ameliorate", "benefit"),
    "WORSENS": ("worsen", "worsens", "worsened", "deteriorate"),
    "CAUSES": ("cause", "causes", "caused", "induce", "leads to"),
    "DECREASES": ("decrease", "decreases", "decreased", "reduce", "reduces"),
    "INCREASES": ("increase", "increases", "increased", "raise", "raises"),
    "PREVENTS": ("prevent", "prevents", "prevented"),
    "DIAGNOSES": ("diagnose", "diagnoses", "diagnosed", "detect", "identifies"),
    "HAS_PHENOTYPE": ("has", "presents with", "characterized by"),
    "ASSOCIATED_WITH": ("associated with", "linked to", "related to"),
}

POPULATION_TERMS = {
    "infant": ("infant", "infants", "newborn", "neonate", "neonates"),
    "child": ("child", "children", "pediatric", "paediatric"),
    "adolescent": ("adolescent", "adolescents", "teenager", "teenagers"),
    "adult": ("adult", "adults"),
    "older_adult": ("elderly", "older adults", "aged patients"),
}


def validate_claim_evidence(claim, context, judge=None):
    evidence_records = _referenced_aligned_triples(claim, context)
    claim_type = infer_claim_type(claim)
    critical = claim_type in CRITICAL_CLAIM_TYPES
    if not evidence_records:
        return _result(claim, "insufficient", critical, ["no_direct_text_evidence"])

    classified = [_classify_record(claim, record) for record in evidence_records]
    labels = [item["label"] for item in classified]
    evidence_results = [item["evidence_result"] for item in classified]
    violations = list(
        dict.fromkeys(
            violation
            for item in classified
            for violation in item["violations"]
        )
    )
    if "contradicted" in labels:
        if "entailed" in labels:
            violations.append("conflicting_cited_evidence")
        return _result(
            claim,
            "contradicted",
            critical,
            list(dict.fromkeys(violations)),
            evidence_results=evidence_results,
        )
    if labels and all(label == "entailed" for label in labels):
        return _result(
            claim,
            "entailed",
            critical,
            [],
            evidence_results=evidence_results,
        )
    hard_failures = {
        "numeric_mismatch",
        "negation_mismatch",
        "population_mismatch",
        "entity_mismatch",
        "entity_incomplete",
        "relation_polarity_mismatch",
    }
    if judge is not None and not hard_failures.intersection(violations):
        return _judge_claim(claim, evidence_records, critical, judge)
    if "unrelated" in labels and "entailed" not in labels:
        label = "unrelated"
    else:
        label = "insufficient"
    if "entailed" in labels and any(item != "entailed" for item in labels):
        violations.append("mixed_citation_support")
    return _result(
        claim,
        label,
        critical,
        list(dict.fromkeys(violations or ["direct_rule_not_satisfied"])),
        evidence_results=evidence_results,
    )


def _classify_record(claim, record):
    text = _normalize_text(claim.get("text", ""))
    evidence_text = _normalize_text(record.get("evidence_text", ""))
    claim_numbers = _numbers(text)
    if claim_numbers and not claim_numbers.issubset(_numbers(evidence_text)):
        return _classification(record, "contradicted", "numeric_mismatch", "numeric_rule")
    if _is_negated(text) != _is_negated(evidence_text):
        return _classification(record, "contradicted", "negation_mismatch", "negation_rule")
    claim_populations = _populations(text)
    evidence_populations = _populations(evidence_text)
    if (
        claim_populations
        and evidence_populations
        and claim_populations.isdisjoint(evidence_populations)
    ):
        return _classification(record, "insufficient", "population_mismatch", "population_rule")
    entity_1 = _normalize_text(record.get("entity_1", {}).get("name", ""))
    entity_2 = _normalize_text(record.get("entity_2", {}).get("name", ""))
    entity_matches = (bool(entity_1 and entity_1 in text), bool(entity_2 and entity_2 in text))
    if not any(entity_matches):
        return _classification(record, "unrelated", "entity_mismatch", "entity_rule")
    if not all(entity_matches):
        return _classification(record, "insufficient", "entity_incomplete", "entity_rule")
    relation = normalize_relation(record.get("relation", ""))
    evidence_polarity = relation_polarity(relation)
    claim_polarities = _claim_polarities(text)
    if (
        evidence_polarity in {"positive", "negative"}
        and claim_polarities
        and evidence_polarity not in claim_polarities
    ):
        return _classification(
            record,
            "contradicted",
            "relation_polarity_mismatch",
            "relation_polarity_rule",
        )
    relation_terms = RELATION_TERMS.get(relation, ())
    if any(term in text for term in relation_terms):
        return _classification(record, "entailed", "", "triple_rule")
    return _classification(
        record,
        "insufficient",
        "direct_rule_not_satisfied",
        "triple_rule",
    )


def _classification(record, label, violation, method):
    return {
        "label": label,
        "violations": [violation] if violation else [],
        "evidence_result": _evidence_result(record, label, method),
    }


def validate_answer_semantics(payload, context, judge=None, mode="enforce"):
    normalized_mode = str(mode or "enforce").strip().lower()
    if normalized_mode not in {"off", "audit", "enforce"}:
        raise ValueError(f"Unsupported semantic validation mode: {mode}")
    if normalized_mode == "off":
        return {
            "passed": True,
            "semantic_passed": False,
            "mode": "off",
            "claim_results": [],
            "violations": [],
        }

    claim_results = [
        validate_claim_evidence(claim, context, judge=judge)
        for claim in payload.get("claims", [])
    ]
    violations = []
    for result in claim_results:
        if result["label"] != "entailed":
            violations.append(f"claim_not_entailed:{result['claim_id']}")
            if result["critical"]:
                violations.append(f"critical_claim_not_entailed:{result['claim_id']}")
    semantic_passed = not violations
    return {
        "passed": semantic_passed or normalized_mode == "audit",
        "semantic_passed": semantic_passed,
        "mode": normalized_mode,
        "claim_results": claim_results,
        "violations": violations,
    }


def _referenced_aligned_triples(claim, context):
    referenced = {
        str(item).strip()
        for item in claim.get("supporting_evidence_ids", [])
        if str(item).strip()
    }
    cited_pmids = {
        str(item).strip()
        for item in claim.get("supporting_pmids", [])
        if str(item).strip()
    }
    return [
        record
        for record in context.get("aligned_triples", [])
        if str(record.get("evidence_id", "")).strip() in referenced
        and str(record.get("source_pmid", "")).strip() in cited_pmids
        and str(record.get("evidence_text", "")).strip()
    ]


def _result(claim, label, critical, violations, evidence_results=None):
    return {
        "claim_id": str(claim.get("claim_id", "")),
        "claim_type": infer_claim_type(claim),
        "label": label,
        "passed": label == "entailed",
        "critical": critical,
        "violations": list(violations),
        "evidence_results": list(evidence_results or []),
    }


def _normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def infer_claim_type(claim):
    explicit = str(claim.get("claim_type", "")).strip().lower()
    if explicit in {
        *CRITICAL_CLAIM_TYPES,
        "prognosis",
        "mechanism",
        "association",
        "other",
    }:
        return explicit
    text = _normalize_text(claim.get("text", ""))
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|ml|dose|doses)\b", text):
        return "dosage"
    if any(term in text for term in ("contraindicat", "must not receive", "should not receive")):
        return "contraindication"
    if any(term in text for term in ("diagnos", "detect", "test", "screen")):
        return "diagnosis"
    if any(term in text for term in ("adverse", "side effect", "safety", "risk of")):
        return "safety"
    if any(term in text for term in ("treat", "therap", "administer", "receive")):
        return "treatment"
    return "other"


def _is_negated(text):
    return bool(re.search(r"\b(?:no|not|never|without|neither|failed to|did not|does not)\b", text))


def _numbers(text):
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))


def _claim_polarities(text):
    polarities = set()
    for relation, terms in RELATION_TERMS.items():
        if any(term in text for term in terms):
            polarity = relation_polarity(relation)
            if polarity in {"positive", "negative"}:
                polarities.add(polarity)
    return polarities


def _populations(text):
    return {
        population
        for population, terms in POPULATION_TERMS.items()
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)
    }


def _evidence_result(record, label, method):
    return {
        "evidence_id": record.get("evidence_id", ""),
        "pmid": str(record.get("source_pmid", "")),
        "label": label,
        "method": method,
        "evidence_text": record.get("evidence_text", ""),
    }


def _judge_claim(claim, evidence_records, critical, judge):
    try:
        judged = judge(claim=claim, evidence_records=evidence_records)
    except Exception as exc:
        return _result(
            claim,
            "insufficient",
            critical,
            [f"judge_failed:{type(exc).__name__}"],
        )
    if not isinstance(judged, dict):
        return _result(claim, "insufficient", critical, ["judge_result_not_object"])
    label = str(judged.get("label", "")).strip().lower()
    if label not in {"entailed", "contradicted", "insufficient", "unrelated"}:
        return _result(claim, "insufficient", critical, ["judge_label_invalid"])
    quote = str(judged.get("matched_quote", "")).strip()
    source_texts = [
        _normalize_text(record.get("evidence_text", ""))
        for record in evidence_records
    ]
    if label == "entailed" and (
        not quote or not any(_normalize_text(quote) in source for source in source_texts)
    ):
        return _result(claim, "insufficient", critical, ["judge_quote_not_in_evidence"])
    first = evidence_records[0]
    evidence_result = {
        **_evidence_result(first, label, "llm_judge"),
        "score": float(judged.get("score", 0.0)),
        "matched_quote": quote,
        "reason": str(judged.get("reason", "")).strip(),
    }
    violations = [] if label == "entailed" else [f"judge_{label}"]
    return _result(
        claim,
        label,
        critical,
        violations,
        evidence_results=[evidence_result],
    )
