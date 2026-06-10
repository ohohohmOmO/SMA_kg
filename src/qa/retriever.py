import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evidence.context_builder import EvidenceContextBuilder


class GraphRagRetriever:
    def __init__(self, builder=None):
        self.builder = builder or EvidenceContextBuilder()

    def retrieve(self, question, top_k=8):
        return self.builder.build_question_context(question, top_k=top_k)


def context_to_prompt(question_or_context, context=None):
    if context is None:
        context = question_or_context
        question = context.get("query", "")
    else:
        question = question_or_context
    payload = {
        "question": question,
        "entities": context.get("entities", []),
        "abstracts": context.get("abstracts", []),
        "aligned_triples": context.get("aligned_triples", []),
        "fused_edges": context.get("fused_edges", []),
        "conflicts": context.get("conflicts", []),
        "supporting_pmids": context.get("supporting_pmids", []),
        "missing_evidence": context.get("missing_evidence", []),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
