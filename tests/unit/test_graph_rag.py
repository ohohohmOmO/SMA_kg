import json
import tempfile
import unittest
from pathlib import Path

from src.evidence.context_builder import EvidenceContextBuilder
from src.qa.answer import build_dry_run_answer
from src.qa.retriever import GraphRagRetriever, context_to_prompt


def write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


class GraphRagTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        e1 = {"name": "SMN1", "type": "Gene"}
        e2 = {"name": "spinal muscular atrophy", "type": "Disease"}
        write_jsonl(root / "abstracts.jsonl", [{"pmid": "10", "title": "SMN1", "abstract": "SMN1 loss causes SMA."}])
        write_jsonl(
            root / "aligned.jsonl",
            [{"source_pmid": "10", "entity_1": e1, "relation": "CAUSES", "entity_2": e2, "evidence_text": "SMN1 loss causes SMA."}],
        )
        write_jsonl(
            root / "fused.jsonl",
            [{"entity_1": e1, "relation": "CAUSES", "entity_2": e2, "computed_confidence": 0.95, "evidence": {"pmid_list": ["10"]}}],
        )
        write_jsonl(root / "conflicts.jsonl", [])
        self.builder = EvidenceContextBuilder(
            abstracts_file=root / "abstracts.jsonl",
            aligned_triples_file=root / "aligned.jsonl",
            fused_triples_file=root / "fused.jsonl",
            conflicts_file=root / "conflicts.jsonl",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_retriever_returns_evidence_context(self):
        context = GraphRagRetriever(builder=self.builder).retrieve("What causes spinal muscular atrophy?")

        self.assertEqual(context["purpose"], "graph_rag_answer")
        self.assertEqual(context["supporting_pmids"], ["10"])
        self.assertEqual(context["retrieval"]["mode"], "lexical_entity")

    def test_prompt_and_dry_run_answer_are_structured(self):
        context = GraphRagRetriever(builder=self.builder).retrieve("What causes SMA?")

        prompt = context_to_prompt("What causes SMA?", context)
        parsed = json.loads(prompt)
        answer = build_dry_run_answer("What causes SMA?", context)

        self.assertEqual(parsed["question"], "What causes SMA?")
        self.assertEqual(answer["question"], "What causes SMA?")
        self.assertEqual(answer["supporting_pmids"], ["10"])
        self.assertEqual(answer["answer_status"], "dry_run_requires_llm")


if __name__ == "__main__":
    unittest.main()
