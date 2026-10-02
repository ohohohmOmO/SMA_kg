"""Conservative identity shared by fusion and database import.

Official IDs attach only to exact symbols, never generic SMN/protein/exon names.
"""
import hashlib
import json
import re
import unicodedata

AUTHORITY = {
    "SMN1": {"ncbi_gene": "6606", "ensembl": "ENSG00000172062"},
    "SMN2": {"ncbi_gene": "6607", "ensembl": "ENSG00000205571"},
}


def identity_form(name):
    # NFC preserves compatibility distinctions; punctuation/digits/qualifiers stay.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(name)).strip()).casefold()


def authority_ids(entity):
    if entity.get("type") == "Gene":
        return dict(AUTHORITY.get(str(entity.get("name", "")).strip().upper(), {}))
    return {}


def compatible_identity(etype, first, second):
    a, b = authority_ids({"type": etype, "name": first}), authority_ids({"type": etype, "name": second})
    if a != b and (a or b):
        return False
    return identity_form(first) == identity_form(second)


def identity_conflict(etype, first, second):
    a, b = authority_ids({"type": etype, "name": first}), authority_ids({"type": etype, "name": second})
    if a and b and a != b:
        return "different_authoritative_gene_ids"
    def subtype(name):
        match = re.search(r"\btype\s*([0-4]|iv|iii|ii|i)\b", name, re.I)
        if match:
            value = match.group(1).casefold()
            return {"i": "1", "ii": "2", "iii": "3", "iv": "4"}.get(value, value)
        match = re.fullmatch(r"sma([0-4])", name, re.I)
        return match.group(1) if match else None
    if etype in {"Disease", "Phenotype", "Variant"} and subtype(first) != subtype(second):
        return "subtype_qualifier_changed"
    return None


def entity_id(entity, namespace="literature"):
    etype, name = entity["type"], str(entity["name"]).strip()
    payload = [namespace, etype, name]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
