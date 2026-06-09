import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.confidence import score_fused_group
from src.biomedical.schema import has_conflicting_polarity, normalize_triple, relation_polarity


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def parse_args():
    parser = argparse.ArgumentParser(description="Aggregate aligned triples and flag relation conflicts.")
    parser.add_argument("--input-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--output-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--conflict-file", default="data/interim/relation_conflicts.jsonl")
    parser.add_argument("--rejected-file", default="data/interim/aggregation_rejected.jsonl")
    return parser.parse_args()


def entity_pair_key(triple):
    return (
        triple["entity_1"].get("name", ""),
        triple["entity_1"].get("type", ""),
        triple["entity_2"].get("name", ""),
        triple["entity_2"].get("type", ""),
    )


def main():
    args = parse_args()
    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    conflict_file = Path(args.conflict_file)
    rejected_file = Path(args.rejected_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    conflict_file.parent.mkdir(parents=True, exist_ok=True)
    rejected_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        logging.error("Input file %s not found.", input_file)
        return 1

    logging.info("Aggregating aligned triples...")

    grouped_data = defaultdict(lambda: {
        "pmid_set": set(),
        "engines_set": set(),
        "sample_data": None,
        "raw_records": [],
    })

    raw_count = 0
    rejected_count = 0
    with input_file.open("r", encoding="utf-8") as f, rejected_file.open("w", encoding="utf-8") as rejected:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            raw_count += 1
            data = json.loads(line)
            normalized, problems = normalize_triple(data, require_evidence=False)
            if problems:
                rejected.write(json.dumps({
                    "line": line_no,
                    "problems": problems,
                    "record": data,
                }, ensure_ascii=False) + "\n")
                rejected_count += 1
                continue

            e1_name = normalized["entity_1"].get("name", "")
            e1_type = normalized["entity_1"].get("type", "")
            rel = normalized.get("relation", "")
            e2_name = normalized["entity_2"].get("name", "")
            e2_type = normalized["entity_2"].get("type", "")
            key = (e1_name, e1_type, rel, e2_name, e2_type)

            group = grouped_data[key]
            group["pmid_set"].add(str(normalized.get("source_pmid", "UNKNOWN")))
            group["engines_set"].add(normalized.get("extracted_by", "UNKNOWN"))
            group["raw_records"].append(normalized)

            if not group["sample_data"]:
                group["sample_data"] = normalized

    fused_triples = []
    pair_to_relations = defaultdict(set)
    pair_to_indices = defaultdict(list)

    for key in sorted(grouped_data, key=lambda item: tuple(str(part).lower() for part in item)):
        group = grouped_data[key]
        base = group["sample_data"]
        engines_list = sorted(group["engines_set"])
        pmid_list = sorted(group["pmid_set"])
        final_conf, confidence_components = score_fused_group(
            group["raw_records"],
            pmid_list,
            engines_list,
        )

        fused_triple = {
            "entity_1": base["entity_1"],
            "relation": base["relation"],
            "entity_2": base["entity_2"],
            "evidence": {
                "pmid_list": pmid_list,
                "extraction_engines": engines_list,
                "evidence_count": len(group["raw_records"]),
            },
            "computed_confidence": final_conf,
            "confidence_components": confidence_components,
            "relation_polarity": relation_polarity(base["relation"]),
            "review_status": "accepted",
        }
        pair_key = entity_pair_key(fused_triple)
        pair_to_relations[pair_key].add(fused_triple["relation"])
        pair_to_indices[pair_key].append(len(fused_triples))
        fused_triples.append(fused_triple)

    conflicts = []
    for pair_key, relations in sorted(pair_to_relations.items(), key=lambda item: item[0]):
        if not has_conflicting_polarity(relations):
            continue
        conflict = {
            "entity_1": {"name": pair_key[0], "type": pair_key[1]},
            "entity_2": {"name": pair_key[2], "type": pair_key[3]},
            "relations": sorted(relations),
            "review_status": "needs_review",
            "reason": "positive_and_negative_relation_polarity",
        }
        conflicts.append(conflict)
        for idx in pair_to_indices[pair_key]:
            fused_triples[idx]["review_status"] = "needs_review"
            fused_triples[idx]["conflict_reason"] = conflict["reason"]
            fused_triples[idx]["conflict_relations"] = conflict["relations"]

    with output_file.open("w", encoding="utf-8") as f:
        for triple in fused_triples:
            f.write(json.dumps(triple, ensure_ascii=False) + "\n")

    with conflict_file.open("w", encoding="utf-8") as f:
        for conflict in conflicts:
            f.write(json.dumps(conflict, ensure_ascii=False) + "\n")

    logging.info("Aggregated %s raw triples into %s fused unique edges.", raw_count, len(fused_triples))
    logging.info("Rejected %s invalid aligned triples to %s.", rejected_count, rejected_file)
    logging.info("Flagged %s conflicting entity pairs to %s.", len(conflicts), conflict_file)
    logging.info("Saved fused triples to %s.", output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
