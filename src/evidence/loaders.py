import csv
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_repo_path(path):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def display_path(path):
    path = Path(path)
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path):
    path = Path(path)
    records = []
    bad_lines = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                bad_lines.append({"line": line_no, "error": str(exc), "raw": line[:500]})
    return records, bad_lines


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def count_jsonl_records(path):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def load_abstracts_by_pmid(path):
    records, bad_lines = load_jsonl(path)
    if bad_lines:
        raise ValueError(f"Abstract file has {len(bad_lines)} invalid JSON lines: {path}")
    abstracts = {}
    for record in records:
        pmid = str(record.get("pmid", "")).strip()
        if not pmid:
            continue
        abstracts[pmid] = {
            "pmid": pmid,
            "title": str(record.get("title", "")).strip(),
            "abstract": str(record.get("abstract", "")).strip(),
            "pub_date": str(record.get("pub_date", "")).strip(),
        }
    return abstracts


def load_analytics_by_entity(path):
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    analytics = {}
    for row in rows:
        entity = str(row.get("Entity", "")).strip()
        if not entity:
            continue
        analytics[entity] = {
            "entity": entity,
            "type": row.get("Type", ""),
            "pagerank": _safe_float(row.get("PageRank")),
            "community_id": _safe_int(row.get("Community_ID")),
        }
    return analytics


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=-1):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

