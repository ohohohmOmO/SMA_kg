import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evidence.loaders import write_json
from src.qa.answer import DEFAULT_MODEL, build_dry_run_answer, generate_answer
from src.qa.neo4j_neighborhood import attach_neo4j_neighborhood
from src.qa.retriever import GraphRagRetriever


def parse_args():
    parser = argparse.ArgumentParser(description="Run local-retrieval-first Graph RAG over the SMA knowledge graph.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--retrieval-mode", choices=["lexical_entity", "hybrid_tfidf"], default="lexical_entity")
    parser.add_argument("--include-neo4j-neighborhood", action="store_true")
    parser.add_argument("--neo4j-neighbor-limit", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--output-file", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    retriever = GraphRagRetriever()
    context = retriever.retrieve(args.question, top_k=args.top_k, retrieval_mode=args.retrieval_mode)
    if args.include_neo4j_neighborhood:
        context = attach_neo4j_neighborhood(context, limit=args.neo4j_neighbor_limit)
    if args.dry_run:
        result = build_dry_run_answer(args.question, context)
    else:
        result = generate_answer(args.question, context, model=args.model, max_tokens=args.max_tokens)
    if args.output_file:
        write_json(REPO_ROOT / args.output_file, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
