import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.schema import normalize_entity_type, normalize_relation


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEFAULT_DICTIONARY = REPO_ROOT / "resources" / "entity_dictionary.json"


def load_dictionary(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def map_entity(entity, dictionary):
    entity = dict(entity or {})
    name = str(entity.get("name", "")).strip()
    etype = normalize_entity_type(entity.get("type")) or str(entity.get("type", "")).strip()
    lower_name = name.lower()
    mapped_name = dictionary.get(etype.lower(), {}).get(lower_name)
    entity["name"] = mapped_name or name
    entity["type"] = etype
    return entity


def parse_args():
    parser = argparse.ArgumentParser(description="Normalize entity names and relation aliases.")
    parser.add_argument("--input-file", default="data/processed/extracted_triples.jsonl")
    parser.add_argument("--output-file", default="data/interim/mapped_triples.jsonl")
    parser.add_argument("--dictionary-file", default=str(DEFAULT_DICTIONARY))
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    dictionary = load_dictionary(args.dictionary_file)

    if not input_file.exists():
        logging.error("File %s not found.", input_file)
        return 1

    mapped_count = 0
    entity_mapping_hits = Counter()
    relation_mapping_hits = Counter()
    with input_file.open("r", encoding="utf-8") as f_in, output_file.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            if not line.strip():
                continue
            data = json.loads(line)

            before_e1 = data.get("entity_1", {}).get("name", "")
            before_e2 = data.get("entity_2", {}).get("name", "")
            before_relation = data.get("relation", "")

            data["entity_1"] = map_entity(data.get("entity_1", {}), dictionary)
            data["entity_2"] = map_entity(data.get("entity_2", {}), dictionary)
            data["relation"] = normalize_relation(before_relation) or before_relation

            if data["entity_1"].get("name") != before_e1:
                entity_mapping_hits[data["entity_1"].get("type", "Unknown")] += 1
            if data["entity_2"].get("name") != before_e2:
                entity_mapping_hits[data["entity_2"].get("type", "Unknown")] += 1
            if data["relation"] != before_relation:
                relation_mapping_hits[f"{before_relation}->{data['relation']}"] += 1

            f_out.write(json.dumps(data, ensure_ascii=False) + "\n")
            mapped_count += 1

    logging.info("Dictionary/relation mapping complete. Processed %s triples to %s.", mapped_count, output_file)
    logging.info("Entity mapping hits by type: %s", dict(entity_mapping_hits))
    logging.info("Relation mapping hits: %s", dict(relation_mapping_hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
