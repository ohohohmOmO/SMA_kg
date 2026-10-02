"""Read-only structural/provenance checks; never assigns human support labels."""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.schema import normalize_triple

DEFAULT_CANDIDATES = "artifacts/runs/stage2_gold_candidates_400_2026-10-01/gold_candidates.jsonl"
DEFAULT_WORKBOOK = "outputs/fyp_gold_annotation_2026-10-01/SMA人工标注集_400条.xlsx"


def load_jsonl(path):
    records, errors = [], []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("record is not an object")
                records.append(value)
            except (ValueError, TypeError) as error:
                errors.append({"line": line_number, "error": str(error)})
    return records, errors


def signature(record):
    return (record["entity_1"]["name"], record["entity_1"]["type"], record["relation"],
            record["entity_2"]["name"], record["entity_2"]["type"])


def candidate_signature(record):
    return (record["entity_1_name"], record["entity_1_type"], record["relation"],
            record["entity_2_name"], record["entity_2_type"])


def locate_evidence(record, abstracts):
    """Text-location diagnostic only: a found span does not establish entailment."""
    source = abstracts.get(str(record.get("source_pmid", "")))
    if source is None:
        return "missing_source"
    span = str(record.get("evidence_text", "")).strip()
    if not span:
        return "missing_evidence"
    texts = [str(source.get(field, "")) for field in ("title", "abstract")]
    if any(span in text for text in texts):
        return "exact"
    normalize = lambda value: re.sub(r"\s+", " ", value).strip().casefold()
    if any(normalize(span) in normalize(text) for text in texts):
        return "case_whitespace_match"
    return "not_located"


def read_annotation_workbook(path):
    """Read the named worksheet via OOXML without Excel or workbook mutation."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            tree = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(node.itertext()) for node in tree.findall("s:si", ns)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(s for s in workbook.findall("s:sheets/s:sheet", ns) if s.get("name") == "标注表")
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_id = sheet.get("{" + ns["r"] + "}id")
        target = next(r.get("Target") for r in rels if r.get("Id") == rel_id)
        member = target.lstrip("/") if target.startswith("/") else "xl/" + target
        tree = ET.fromstring(archive.read(member))
        headers, records = {}, []
        for row in tree.findall("s:sheetData/s:row", ns):
            values = {}
            for cell in row.findall("s:c", ns):
                column = re.sub(r"\d", "", cell.get("r", ""))
                value = cell.findtext("s:v", default="", namespaces=ns)
                if cell.get("t") == "s":
                    value = strings[int(value)]
                elif cell.get("t") == "inlineStr":
                    value = "".join(t.text or "" for t in cell.findall("s:is//s:t", ns))
                values[column] = value
            if row.get("r") == "1":
                headers = values
            elif values.get("A"):
                records.append({headers.get(column, column): value for column, value in values.items()})
        return records


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, help="New dated output directory; inputs are never written.")
    parser.add_argument("--candidates-file", default=DEFAULT_CANDIDATES)
    parser.add_argument("--workbook", default=DEFAULT_WORKBOOK)
    args = parser.parse_args()
    paths = {"abstracts": REPO_ROOT / "data/raw/pubmed_sma_abstracts.jsonl",
             "raw": REPO_ROOT / "data/processed/extracted_triples.jsonl",
             "mapped": REPO_ROOT / "data/interim/mapped_triples.jsonl",
             "aligned": REPO_ROOT / "data/interim/aligned_triples.jsonl",
             "fused": REPO_ROOT / "data/processed/fused_triples.jsonl",
             "conflicts": REPO_ROOT / "data/interim/relation_conflicts.jsonl",
             "candidates": REPO_ROOT / args.candidates_file,
             "workbook": REPO_ROOT / args.workbook}
    out = (REPO_ROOT / args.run_dir).resolve()
    # Fail before touching existing outputs or any source file.
    out.mkdir(parents=True, exist_ok=False)
    data, summary, issues = {}, {}, []
    for name, path in paths.items():
        if name == "workbook":
            continue
        data[name], parse_errors = load_jsonl(path)
        summary[name] = {"records": len(data[name]), "parse_errors": len(parse_errors)}
        issues.extend({"file": name, **item} for item in parse_errors)
    abstracts = {str(row.get("pmid", "")): row for row in data["abstracts"]}
    summary["abstracts"]["duplicate_pmids"] = len(data["abstracts"]) - len(abstracts)
    if summary["abstracts"]["duplicate_pmids"]:
        issues.append({"file": "abstracts", "error": "duplicate PMID keys"})

    for name in ("raw", "mapped", "aligned"):
        schema_errors, missing_sources = 0, 0
        for row in data[name]:
            _, problems = normalize_triple(row)
            schema_errors += bool(problems)
            missing_sources += str(row.get("source_pmid", "")) not in abstracts
        summary[name].update(schema_invalid=schema_errors, missing_sources=missing_sources)
        if schema_errors or missing_sources:
            issues.append({"file": name, "schema_invalid": schema_errors, "missing_sources": missing_sources})

    location_counts, location_queue = Counter(), []
    for index, row in enumerate(data["raw"], 1):
        state = locate_evidence(row, abstracts)
        location_counts[state] += 1
        if state not in ("exact", "case_whitespace_match"):
            location_queue.append({"raw_record_number": index, "location_status": state, **row})
    summary["evidence_location"] = dict(location_counts)
    # Non-located text is a review flag, not a factuality verdict or schema failure.
    write_jsonl(out / "evidence_location_review.jsonl", location_queue)

    expected = defaultdict(list)
    for row in data["aligned"]:
        expected[signature(row)].append(row)
    seen, fused_errors = set(), 0
    for row in data["fused"]:
        key = signature(row)
        records = expected.get(key, [])
        pmids = row.get("evidence", {}).get("pmid_list", [])
        expected_pmids = {str(r.get("source_pmid", "")) for r in records}
        count = row.get("evidence", {}).get("evidence_count")
        bad = key in seen or not records or set(map(str, pmids)) != expected_pmids
        bad = bad or len(pmids) != len(set(map(str, pmids))) or count != len(records)
        fused_errors += bool(bad)
        seen.add(key)
    missing_keys = len(set(expected) - seen)
    summary["fused"].update(provenance_or_count_errors=fused_errors, missing_aligned_groups=missing_keys,
                            review_status=dict(Counter(r.get("review_status", "") for r in data["fused"])))
    if fused_errors or missing_keys:
        issues.append({"file": "fused", "provenance_or_count_errors": fused_errors,
                       "missing_aligned_groups": missing_keys})

    changes, unchanged_fields_errors = {}, 0
    equal_counts = len(data["raw"]) == len(data["mapped"]) == len(data["aligned"])
    if not equal_counts:
        issues.append({"error": "raw/mapped/aligned counts differ; row-based change comparison skipped"})
    else:
        for raw, mapped, aligned in zip(data["raw"], data["mapped"], data["aligned"]):
            stable_fields = ("source_pmid", "relation", "evidence_text")
            unchanged_fields_errors += any(mapped.get(f) != aligned.get(f) for f in stable_fields)
            for field in ("entity_1", "entity_2"):
                unchanged_fields_errors += mapped[field]["type"] != aligned[field]["type"]
                key = (mapped[field]["type"], raw[field]["name"], mapped[field]["name"], aligned[field]["name"])
                if len(set(key[1:])) > 1:
                    changes.setdefault(key, {"entity_type": key[0], "raw_name": key[1], "dictionary_name": key[2],
                                             "aligned_name": key[3], "example_pmid": str(raw["source_pmid"])})
    summary["alignment"] = {"changed_name_mappings": len(changes),
                             "unexpected_field_changes": unchanged_fields_errors}
    if unchanged_fields_errors:
        issues.append({"file": "aligned", "unexpected_field_changes": unchanged_fields_errors})
    write_jsonl(out / "alignment_review_candidates.jsonl", list(changes.values()))

    conflict_queue, missing_conflict_relations = [], 0
    for index, conflict in enumerate(data["conflicts"], 1):
        for relation in conflict.get("relations", []):
            key = (conflict["entity_1"]["name"], conflict["entity_1"]["type"], relation,
                   conflict["entity_2"]["name"], conflict["entity_2"]["type"])
            records = expected.get(key, [])
            missing_conflict_relations += not records
            conflict_queue.append({"conflict_id": f"SMA-CONFLICT-{index:04d}", "relation": relation,
                                   "entity_1": conflict["entity_1"], "entity_2": conflict["entity_2"],
                                   "source_evidence": [{"pmid": str(r.get("source_pmid", "")),
                                                        "evidence_text": r.get("evidence_text", "")} for r in records],
                                   "human_review_status": "pending_review"})
    summary["conflicts"]["missing_relation_sources"] = missing_conflict_relations
    if missing_conflict_relations:
        issues.append({"file": "conflicts", "missing_relation_sources": missing_conflict_relations})
    write_jsonl(out / "conflict_review_candidates.jsonl", conflict_queue)

    candidate_rows = {r["candidate_id"]: r for r in data["candidates"]}
    raw_signatures = {(str(r.get("source_pmid", "")), signature(r)) for r in data["raw"]}
    candidate_errors = 0
    for row in data["candidates"]:
        source = abstracts.get(str(row.get("source_pmid", "")), {})
        candidate_errors += (str(row.get("source_pmid", "")), candidate_signature(row)) not in raw_signatures
        candidate_errors += any(row.get(f, "") != source.get(f, "") for f in ("title", "abstract"))
    workbook = read_annotation_workbook(paths["workbook"])
    protected = ("sample_group", "requires_second_review", "source_pmid", "title", "abstract", "entity_1_name",
                 "entity_1_type", "relation", "entity_2_name", "entity_2_type", "evidence_text")
    wb_ids = [r.get("candidate_id") for r in workbook]
    workbook_errors = len(wb_ids) - len(set(wb_ids)) + len(set(wb_ids) ^ set(candidate_rows))
    for row in workbook:
        original = candidate_rows.get(row.get("candidate_id"), {})
        workbook_errors += sum(str(row.get(f, "")) != str(original.get(f, "")) for f in protected)
    summary["candidates"].update(source_or_signature_errors=candidate_errors,
                                  duplicate_ids=len(data["candidates"]) - len(candidate_rows),
                                  groups=dict(Counter(r.get("sample_group", "") for r in data["candidates"])))
    summary["workbook"] = {"records": len(workbook), "protected_input_errors": workbook_errors,
                           "support_labels_entered": sum(bool(r.get("support_label", "")) for r in workbook),
                           "review_status": dict(Counter(r.get("review_status", "") for r in workbook)),
                           "required_second_reviews": sum(r.get("requires_second_review") == "yes" for r in workbook)}
    if candidate_errors or workbook_errors or summary["candidates"]["duplicate_ids"]:
        issues.append({"file": "candidates/workbook", "candidate_errors": candidate_errors,
                       "protected_input_errors": workbook_errors,
                       "duplicate_candidate_ids": summary["candidates"]["duplicate_ids"]})

    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "structural_issue_count": len(issues),
              "checks": summary, "issues": issues,
              "limits": ["No human labels are assigned or interpreted as final metrics.",
                         "Text matching is not semantic support validation.",
                         "No database connection, API call, or canonical-output write is performed."]}
    (out / "validation_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_rows = []
    for name, path in list(paths.items()) + [(p.name, p) for p in sorted(out.iterdir()) if p.is_file()]:
        manifest_rows.append({"artifact": name, "path": str(path.resolve()), "bytes": path.stat().st_size,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["artifact", "path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
