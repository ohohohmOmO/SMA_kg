import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def merge_jsonl(files_list, output_file):
    merged_triples = []
    seen_signatures = set()

    for file_path in files_list:
        if not Path(file_path).exists():
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                pmid = data.get("source_pmid", "UNKNOWN")
                e1 = data.get("entity_1", {}).get("name", "").lower()
                rel = data.get("relation", "").upper()
                e2 = data.get("entity_2", {}).get("name", "").lower()

                sig = f"{pmid}_{e1}_{rel}_{e2}"
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    merged_triples.append(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        for t in merged_triples:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    logging.info(f"Merge complete. Saved {len(merged_triples)} unique triples to {output_file}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Create Stage 2 canonical extracted_triples.jsonl. By default this "
            "uses LLM output only; raw rule candidates must not be passed here."
        )
    )
    parser.add_argument("--llm-file", default="data/processed/llm_extracted_triples.jsonl")
    parser.add_argument(
        "--verified-rule-file",
        action="append",
        default=[],
        help="Optional LLM- or human-verified rule candidate JSONL to include.",
    )
    parser.add_argument("--output-file", default="data/processed/extracted_triples.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    merge_jsonl([args.llm_file, *args.verified_rule_file], args.output_file)


if __name__ == "__main__":
    main()
