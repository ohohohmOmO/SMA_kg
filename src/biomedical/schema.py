import copy
import json
import re
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "resources" / "biomedical_schema.json"


def relation_key(value):
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").upper()).strip("_")


@lru_cache(maxsize=4)
def load_schema(path=None):
    schema_path = Path(path) if path else DEFAULT_SCHEMA_PATH
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    schema["entity_types_set"] = set(schema.get("entity_types", []))
    schema["relations_set"] = set(schema.get("relations", {}).keys())
    schema["relation_aliases_normalized"] = {
        relation_key(k): relation_key(v) for k, v in schema.get("relation_aliases", {}).items()
    }
    schema["entity_type_aliases_normalized"] = {
        str(k).strip().lower(): v for k, v in schema.get("entity_type_aliases", {}).items()
    }
    schema["positive_relations_set"] = set(schema.get("positive_relations", []))
    schema["negative_relations_set"] = set(schema.get("negative_relations", []))
    schema["conflict_relation_pairs_set"] = {
        tuple(sorted(pair)) for pair in schema.get("conflict_relation_pairs", [])
    }
    return schema


def normalize_entity_type(raw_type, schema=None):
    schema = schema or load_schema()
    raw = str(raw_type or "").strip()
    if raw in schema["entity_types_set"]:
        return raw
    return schema["entity_type_aliases_normalized"].get(raw.lower(), "")


def normalize_relation(raw_relation, schema=None):
    schema = schema or load_schema()
    key = relation_key(raw_relation)
    if not key:
        return ""
    alias = schema["relation_aliases_normalized"].get(key, key)
    if alias in schema["relations_set"]:
        return alias
    return ""


def relation_polarity(relation, schema=None):
    schema = schema or load_schema()
    canonical = normalize_relation(relation, schema)
    return schema.get("relations", {}).get(canonical, {}).get("polarity", "unknown")


def has_conflicting_polarity(relations, schema=None):
    schema = schema or load_schema()
    canonical = {normalize_relation(rel, schema) for rel in relations}
    canonical.discard("")
    for pair in schema["conflict_relation_pairs_set"]:
        if set(pair).issubset(canonical):
            return True
    return bool(canonical & schema["positive_relations_set"] and canonical & schema["negative_relations_set"])


def clean_entity_name(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_triple(record, schema=None, require_evidence=False):
    schema = schema or load_schema()
    normalized = copy.deepcopy(record)
    problems = []

    pmid = str(normalized.get("source_pmid", "")).strip()
    if not pmid:
        problems.append("missing_source_pmid")
    normalized["source_pmid"] = pmid

    for key in ("entity_1", "entity_2"):
        entity = normalized.get(key)
        if not isinstance(entity, dict):
            problems.append(f"{key}_not_object")
            entity = {}
        name = clean_entity_name(entity.get("name"))
        etype = normalize_entity_type(entity.get("type"), schema)
        if not name:
            problems.append(f"{key}.name_empty")
        if not etype:
            problems.append(f"{key}.type_invalid")
        normalized[key] = {"name": name, "type": etype or str(entity.get("type", "")).strip()}

    original_relation = normalized.get("relation", "")
    relation = normalize_relation(original_relation, schema)
    if not relation:
        problems.append("relation_invalid")
    normalized["relation"] = relation or relation_key(original_relation)
    if relation and relation != relation_key(original_relation):
        normalized["relation_original"] = str(original_relation)

    evidence = normalized.get("evidence")
    evidence_text_raw = normalized.get("evidence_text") or normalized.get("evidence_sentence")
    if not evidence_text_raw and isinstance(evidence, dict):
        evidence_text_raw = evidence.get("text", "")
    evidence_text = clean_entity_name(evidence_text_raw)
    if evidence_text:
        normalized["evidence_text"] = evidence_text
    elif require_evidence:
        problems.append("evidence_text_empty")

    return normalized, problems


def is_valid_triple(record, schema=None, require_evidence=False):
    _, problems = normalize_triple(record, schema=schema, require_evidence=require_evidence)
    return not problems
