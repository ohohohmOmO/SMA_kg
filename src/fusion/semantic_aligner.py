"""Typed identity normalization; embedding similarity produces review proposals only."""
import argparse
import copy
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.biomedical.entity_identity import identity_form, compatible_identity

DEFAULT_MODEL = "NeuML/pubmedbert-base-embeddings"
POLICY = "typed_orthographic_identity_v2_semantic_review_only"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_canonical_name(cluster, freq_map):
    return min(cluster, key=lambda name: (-freq_map[name], len(name), name.casefold(), name))


def build_alignment_map(triples):
    frequencies = Counter((e["type"], e["name"]) for r in triples
                          for e in (r["entity_1"], r["entity_2"]))
    groups = defaultdict(list)
    for etype, name in frequencies:
        groups[(etype, identity_form(name))].append(name)
    mapping = {}
    for (etype, _), names in sorted(groups.items()):
        typed_frequency = {name: frequencies[(etype, name)] for name in names}
        canonical = get_canonical_name(names, typed_frequency)
        for name in names:
            mapping[(etype, name)] = canonical if compatible_identity(etype, name, canonical) else name
    return mapping


def apply_alignment(triples, mapping):
    result = copy.deepcopy(triples)
    for row in result:
        for key in ("entity_1", "entity_2"):
            entity = row[key]
            entity["name"] = mapping.get((entity["type"], entity["name"]), entity["name"])
    return result


def semantic_proposals(mapping, model_name, threshold, batch_size):
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    model = SentenceTransformer(model_name)
    by_type = defaultdict(set)
    for etype, name in mapping:
        by_type[etype].add(mapping[(etype, name)])
    proposals = []
    for etype, names in sorted(by_type.items()):
        names = sorted(names)
        if len(names) < 2:
            continue
        logging.info("Embedding %s %s names for review only", len(names), etype)
        vectors = model.encode(names, batch_size=batch_size, show_progress_bar=False)
        similarities = cosine_similarity(vectors)
        seen = set()
        for i, name in enumerate(names):
            similarities[i, i] = -1
            j = int(similarities[i].argmax())
            score = float(similarities[i, j])
            pair = tuple(sorted((i, j)))
            if score >= threshold and pair not in seen:
                seen.add(pair)
                proposals.append({"entity_type": etype, "name": name, "candidate": names[j],
                                  "similarity": round(score, 6), "automatic_merge": False,
                                  "identity_compatible": compatible_identity(etype, name, names[j]),
                                  "judgment": "", "reviewer_id": ""})
    return proposals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", default="data/interim/mapped_triples.jsonl")
    parser.add_argument("--output-file", default="data/interim/aligned_triples.jsonl")
    parser.add_argument("--model", default=os.environ.get("STAGE3_ALIGNMENT_MODEL", DEFAULT_MODEL))
    parser.add_argument("--threshold", type=float, default=0.88)
    parser.add_argument("--hf-endpoint", default=os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"))
    parser.add_argument("--propose-semantic", action="store_true")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    output = Path(args.output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    triples = [json.loads(line) for line in Path(args.input_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    mapping = build_alignment_map(triples)
    aligned = apply_alignment(triples, mapping)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in aligned), encoding="utf-8")
    changes = [{"type": t, "original_name": n, "canonical_name": c,
                "reason": "same_typed_orthographic_form"} for (t, n), c in sorted(mapping.items()) if n != c]
    status = "not_requested"
    proposals = []
    if args.propose_semantic:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint
        try:
            proposals = semantic_proposals(mapping, args.model, args.threshold, args.batch_size)
            status = "completed_review_only"
        except Exception as exc:
            status = "failed_" + type(exc).__name__
            logging.error("Semantic proposal generation failed (%s)", type(exc).__name__)
    output.with_suffix(".alignment_audit.json").write_text(json.dumps({"policy": POLICY,
        "records": len(aligned), "changes": changes, "semantic_model": args.model,
        "semantic_threshold": args.threshold, "semantic_status": status,
        "automatic_semantic_merges": 0, "proposals": proposals}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logging.info("Aligned %s records; %s orthographic mapping units; no automatic semantic merges", len(aligned), len(changes))
    return 1 if status.startswith("failed_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
