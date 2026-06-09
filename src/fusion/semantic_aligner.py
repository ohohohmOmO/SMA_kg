import argparse
import json
import logging
import os
import shutil
from collections import defaultdict, deque
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEFAULT_MODEL = "NeuML/pubmedbert-base-embeddings"


def get_canonical_name(cluster, freq_map):
    return sorted(cluster, key=lambda name: (-freq_map[name], len(name), name.lower()))[0]


def connected_components(entity_list, sim_matrix, threshold):
    adjacency = {i: set() for i in range(len(entity_list))}
    for i in range(len(entity_list)):
        for j in range(i + 1, len(entity_list)):
            if sim_matrix[i][j] >= threshold:
                adjacency[i].add(j)
                adjacency[j].add(i)

    visited = set()
    components = []
    for i in range(len(entity_list)):
        if i in visited:
            continue
        queue = deque([i])
        visited.add(i)
        component = []
        while queue:
            current = queue.popleft()
            component.append(entity_list[current])
            for neighbor in sorted(adjacency[current]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component, key=str.lower))
    return sorted(components, key=lambda comp: comp[0].lower())


def parse_args():
    parser = argparse.ArgumentParser(description="Medically aligned deterministic entity semantic normalization.")
    parser.add_argument("--input-file", default="data/interim/mapped_triples.jsonl")
    parser.add_argument("--output-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--model", default=os.environ.get("STAGE3_ALIGNMENT_MODEL", DEFAULT_MODEL))
    parser.add_argument("--threshold", type=float, default=0.88)
    parser.add_argument("--hf-endpoint", default=os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"))
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        logging.error("Input file %s not found.", input_file)
        return 1

    logging.info("Loading triples for semantic alignment...")
    triples = []
    entity_freq = defaultdict(int)
    type_to_entities = defaultdict(set)

    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            triples.append(data)

            for entity_key in ("entity_1", "entity_2"):
                entity = data.get(entity_key, {})
                name = str(entity.get("name", "")).strip()
                etype = str(entity.get("type", "")).strip()
                if not name or not etype:
                    continue
                entity_freq[name] += 1
                type_to_entities[etype].add(name)

    if SentenceTransformer is None:
        logging.warning("sentence-transformers is unavailable. Copying dictionary-mapped input unchanged.")
        shutil.copy(input_file, output_file)
        return 0

    if args.hf_endpoint:
        os.environ.setdefault("HF_ENDPOINT", args.hf_endpoint)
    logging.info("Loading biomedical SentenceTransformer model: %s", args.model)

    try:
        model = SentenceTransformer(args.model)
    except Exception as exc:
        logging.warning("Biomedical semantic model failed to load: %s", exc)
        logging.warning("Bypassing fuzzy semantic alignment. Proceeding with dictionary-mapped alignments.")
        shutil.copy(input_file, output_file)
        return 0

    global_alignment_map = {}

    for etype in sorted(type_to_entities):
        entities = type_to_entities[etype]
        if len(entities) <= 1:
            for entity in entities:
                global_alignment_map[entity] = entity
            continue

        entity_list = sorted(entities, key=str.lower)
        logging.info("Computing embeddings for %s entities of type '%s'.", len(entity_list), etype)
        embeddings = model.encode(entity_list, show_progress_bar=False)
        sim_matrix = cosine_similarity(embeddings)
        components = connected_components(entity_list, sim_matrix, args.threshold)

        for component in components:
            canonical = get_canonical_name(component, entity_freq)
            for entity in component:
                global_alignment_map[entity] = canonical

    logging.info("Applying canonical alignments over dataset...")
    aligned_count = 0
    with output_file.open("w", encoding="utf-8") as f:
        for data in triples:
            for entity_key in ("entity_1", "entity_2"):
                entity = data.get(entity_key, {})
                name = entity.get("name", "")
                if name:
                    entity["name"] = global_alignment_map.get(name, name)
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            aligned_count += 1

    logging.info("Alignment complete. Wrote %s triples to %s.", aligned_count, output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
