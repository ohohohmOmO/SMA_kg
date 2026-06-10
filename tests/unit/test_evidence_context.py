import json
import tempfile
import unittest
from pathlib import Path

from src.evidence.context_builder import EvidenceContextBuilder


def write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


class EvidenceContextBuilderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.abstracts_file = self.root / "abstracts.jsonl"
        self.aligned_file = self.root / "aligned.jsonl"
        self.fused_file = self.root / "fused.jsonl"
        self.conflicts_file = self.root / "conflicts.jsonl"
        self.entity_1 = {"name": "Nusinersen", "type": "Drug"}
        self.entity_2 = {"name": "motor function", "type": "Phenotype"}
        self.conflict = {
            "entity_1": self.entity_1,
            "entity_2": self.entity_2,
            "relations": ["IMPROVES", "WORSENS"],
            "reason": "opposite relation polarity",
            "review_status": "needs_review",
        }
        write_jsonl(
            self.abstracts_file,
            [
                {
                    "pmid": "1",
                    "title": "Nusinersen improves outcomes",
                    "abstract": "Nusinersen improved motor function in SMA patients.",
                    "pub_date": "2024",
                },
                {
                    "pmid": "2",
                    "title": "Adverse response",
                    "abstract": "A subgroup reported worsened motor function after treatment.",
                    "pub_date": "2023",
                },
            ],
        )
        write_jsonl(
            self.aligned_file,
            [
                {
                    "source_pmid": "1",
                    "entity_1": self.entity_1,
                    "relation": "IMPROVES",
                    "entity_2": self.entity_2,
                    "evidence_text": "Nusinersen improved motor function.",
                },
                {
                    "source_pmid": "2",
                    "entity_1": self.entity_1,
                    "relation": "WORSENS",
                    "entity_2": self.entity_2,
                    "evidence_text": "Motor function worsened in a subgroup.",
                },
            ],
        )
        write_jsonl(
            self.fused_file,
            [
                {
                    "entity_1": self.entity_1,
                    "relation": "IMPROVES",
                    "entity_2": self.entity_2,
                    "computed_confidence": 0.91,
                    "review_status": "validated",
                    "evidence": {"pmid_list": ["1"]},
                },
                {
                    "entity_1": self.entity_1,
                    "relation": "WORSENS",
                    "entity_2": self.entity_2,
                    "computed_confidence": 0.73,
                    "review_status": "needs_review",
                    "evidence": {"pmid_list": ["2"]},
                },
            ],
        )
        write_jsonl(self.conflicts_file, [self.conflict])

    def tearDown(self):
        self.tmp.cleanup()

    def build(self):
        return EvidenceContextBuilder(
            abstracts_file=self.abstracts_file,
            aligned_triples_file=self.aligned_file,
            fused_triples_file=self.fused_file,
            conflicts_file=self.conflicts_file,
        )

    def test_build_conflict_context_collects_local_evidence(self):
        context = self.build().build_conflict_context(self.conflict, "SMA-CONFLICT-0001")

        self.assertEqual(context["context_id"], "SMA-CONFLICT-0001")
        self.assertEqual(context["purpose"], "conflict_adjudication")
        self.assertEqual(context["supporting_pmids"], ["1", "2"])
        self.assertEqual(len(context["aligned_triples"]), 2)
        self.assertEqual(len(context["fused_edges"]), 2)
        self.assertEqual({item["pmid"] for item in context["abstracts"]}, {"1", "2"})
        self.assertFalse(context["missing_evidence"])

    def test_missing_abstract_is_reported_without_calling_external_services(self):
        write_jsonl(
            self.aligned_file,
            [
                {
                    "source_pmid": "3",
                    "entity_1": self.entity_1,
                    "relation": "IMPROVES",
                    "entity_2": self.entity_2,
                    "evidence_text": "A missing PMID still remains auditable.",
                }
            ],
        )

        context = self.build().build_conflict_context(self.conflict)

        self.assertEqual(context["supporting_pmids"], ["3", "1", "2"])
        self.assertIn({"kind": "missing_abstract", "pmid": "3"}, context["missing_evidence"])

    def test_build_question_context_uses_local_retrieval(self):
        context = self.build().build_question_context("Does nusinersen improve motor function?")

        self.assertEqual(context["purpose"], "graph_rag_answer")
        self.assertEqual(context["retrieval"]["mode"], "lexical_entity")
        self.assertGreaterEqual(context["retrieval"]["aligned_candidates"], 1)
        self.assertEqual(context["supporting_pmids"], ["1", "2"])


if __name__ == "__main__":
    unittest.main()
