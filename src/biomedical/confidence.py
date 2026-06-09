from statistics import mean

from src.biomedical.schema import load_schema, normalize_triple


ENGINE_RELIABILITY = {
    "LLM": 0.78,
    "Regex_Fallback": 0.45,
    "Rule_Fallback": 0.45,
    "Rule_Candidate": 0.45,
}


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def parse_self_score(record):
    for key in ("llm_confidence", "confidence", "self_confidence", "confidence_score"):
        value = record.get(key)
        if isinstance(value, (int, float)):
            return clamp(value)
        if isinstance(value, str):
            try:
                return clamp(float(value))
            except ValueError:
                continue
    return None


def engine_reliability(extracted_by):
    label = str(extracted_by or "")
    if label.startswith("LLM_") or label == "LLM":
        return ENGINE_RELIABILITY["LLM"]
    return ENGINE_RELIABILITY.get(label, 0.5)


def score_raw_triple(record, problems=None):
    problems = problems or []
    self_score = parse_self_score(record)
    engine_score = engine_reliability(record.get("extracted_by"))
    schema_score = 1.0 if not problems else max(0.0, 1.0 - 0.25 * len(problems))
    evidence_score = 1.0 if record.get("evidence_text") else 0.55
    model_score = self_score if self_score is not None else engine_score
    score = (
        0.38 * model_score
        + 0.24 * evidence_score
        + 0.24 * schema_score
        + 0.14 * engine_score
    )
    return round(clamp(score), 3), {
        "model_or_self_score": round(model_score, 3),
        "evidence_score": round(evidence_score, 3),
        "schema_score": round(schema_score, 3),
        "engine_score": round(engine_score, 3),
        "scoring_version": "raw_v1",
    }


def normalize_and_score(record, schema=None, require_evidence=False):
    schema = schema or load_schema()
    normalized, problems = normalize_triple(record, schema=schema, require_evidence=require_evidence)
    score, components = score_raw_triple(normalized, problems)
    normalized["computed_confidence"] = score
    normalized["confidence_components"] = components
    return normalized, problems


def score_fused_group(raw_records, pmids, engines, schema=None):
    schema = schema or load_schema()
    normalized_scores = []
    schema_valid = []
    for record in raw_records:
        normalized, problems = normalize_triple(record, schema=schema, require_evidence=False)
        score = normalized.get("computed_confidence")
        if not isinstance(score, (int, float)):
            score, _ = score_raw_triple(normalized, problems)
        normalized_scores.append(clamp(score))
        schema_valid.append(not problems)

    base_score = max(normalized_scores) if normalized_scores else 0.0
    avg_score = mean(normalized_scores) if normalized_scores else 0.0
    pmid_support = min(1.0, 0.45 + 0.12 * max(0, len(pmids) - 1))
    engine_support = min(1.0, 0.55 + 0.25 * max(0, len(engines) - 1))
    schema_score = 1.0 if all(schema_valid) else 0.65
    score = (
        0.42 * base_score
        + 0.18 * avg_score
        + 0.18 * pmid_support
        + 0.14 * engine_support
        + 0.08 * schema_score
    )
    return round(clamp(score), 3), {
        "base_score": round(base_score, 3),
        "avg_raw_score": round(avg_score, 3),
        "pmid_support_score": round(pmid_support, 3),
        "engine_support_score": round(engine_support, 3),
        "schema_score": round(schema_score, 3),
        "supporting_pmids": len(pmids),
        "supporting_engines": len(engines),
        "scoring_version": "fused_v1",
    }
