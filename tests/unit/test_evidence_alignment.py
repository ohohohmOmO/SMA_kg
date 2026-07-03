import json
import tempfile
import unittest
from pathlib import Path

from src.biomedical.confidence import score_raw_triple
from src.biomedical.evidence import align_evidence_span
from src.extraction.run_stage2_extraction import validate_triples
from src.extraction.validate_evidence_spans import audit_evidence_spans


class EvidenceAlignmentTest(unittest.TestCase):
    def test_exact_match_returns_original_character_span(self):
        abstract = "Background. Nusinersen improves motor function in SMA."

        alignment = align_evidence_span("Nusinersen improves motor function", abstract)

        self.assertTrue(alignment["valid"])
        self.assertEqual(alignment["method"], "exact")
        self.assertEqual(
            abstract[alignment["start_char"]:alignment["end_char"]],
            "Nusinersen improves motor function",
        )

    def test_normalized_match_tolerates_spacing_and_punctuation(self):
        abstract = "The study found that SMN1-loss causes SMA."

        alignment = align_evidence_span("SMN1 loss causes SMA", abstract)

        self.assertTrue(alignment["valid"])
        self.assertEqual(alignment["method"], "normalized")
        self.assertEqual(alignment["matched_text"], "SMN1-loss causes SMA")

    def test_fuzzy_match_accepts_a_close_local_span(self):
        abstract = "Nusinersen significantly improved overall motor function in children."

        alignment = align_evidence_span(
            "Nusinersen significantly improved motor function in children.",
            abstract,
        )

        self.assertTrue(alignment["valid"])
        self.assertEqual(alignment["method"], "fuzzy")
        self.assertGreaterEqual(alignment["score"], 0.9)

    def test_hallucinated_or_short_fuzzy_evidence_is_rejected(self):
        abstract = "Nusinersen was administered to children with SMA."

        hallucinated = align_evidence_span(
            "Nusinersen completely cured respiratory and motor dysfunction.",
            abstract,
        )
        short = align_evidence_span("cured SMA", abstract, min_fuzzy_score=0.1)

        self.assertFalse(hallucinated["valid"])
        self.assertFalse(short["valid"])

    def test_fuzzy_match_rejects_a_similar_span_with_replaced_biomedical_terms(self):
        abstract = "Other relevant conditions included muscular dystrophy."

        alignment = align_evidence_span(
            "Other relevant conditions included spinal muscular atrophy.",
            abstract,
        )

        self.assertFalse(alignment["valid"])

    def test_aligned_evidence_score_is_used_by_confidence(self):
        score, components = score_raw_triple({
            "evidence_text": "supported",
            "evidence_alignment": {"valid": True, "score": 0.91},
            "llm_confidence": 0.9,
            "extracted_by": "LLM_test",
        })

        self.assertGreater(score, 0)
        self.assertEqual(components["evidence_score"], 0.91)
        self.assertEqual(components["scoring_version"], "raw_v2_evidence_aligned")

    def test_offline_audit_separates_aligned_and_rejected_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            abstracts = root / "abstracts.jsonl"
            triples = root / "triples.jsonl"
            run_dir = root / "run"
            abstracts.write_text(
                json.dumps({
                    "pmid": "1",
                    "title": "Study",
                    "abstract": "Nusinersen improves motor function in SMA.",
                }) + "\n",
                encoding="utf-8",
            )
            records = [
                {
                    "source_pmid": "1",
                    "entity_1": {"name": "Nusinersen", "type": "Drug"},
                    "relation": "IMPROVES",
                    "entity_2": {"name": "motor function", "type": "Phenotype"},
                    "evidence_text": "Nusinersen improves motor function",
                    "llm_confidence": 0.9,
                    "extracted_by": "LLM_test",
                },
                {
                    "source_pmid": "1",
                    "entity_1": {"name": "Nusinersen", "type": "Drug"},
                    "relation": "TREATS",
                    "entity_2": {"name": "SMA", "type": "Disease"},
                    "evidence_text": "Nusinersen permanently cures every SMA patient",
                    "llm_confidence": 0.9,
                    "extracted_by": "LLM_test",
                },
            ]
            triples.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            summary = audit_evidence_spans(triples, abstracts, run_dir, 0.9)

            self.assertTrue(summary["valid"])
            self.assertEqual(summary["records_aligned"], 1)
            self.assertEqual(summary["records_rejected"], 1)
            output = (
                run_dir / "outputs" / "data" / "processed" / "evidence_aligned_triples.jsonl"
            )
            aligned = json.loads(output.read_text(encoding="utf-8").strip())
            self.assertEqual(aligned["evidence_alignment"]["method"], "exact")
            self.assertEqual(
                aligned["confidence_components"]["scoring_version"],
                "raw_v2_evidence_aligned",
            )
            self.assertTrue((run_dir / "manifest.csv").exists())

    def test_stage2_validation_can_require_alignment_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "triples.jsonl"
            record = {
                "source_pmid": "1",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence_text": "Nusinersen improves motor function",
                "computed_confidence": 0.9,
                "extracted_by": "LLM_test",
            }
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")

            missing = validate_triples(path, require_evidence_alignment=True)
            record["evidence_alignment"] = {
                "valid": True,
                "method": "exact",
                "score": 1.0,
                "start_char": 0,
                "end_char": 35,
                "matched_text": "Nusinersen improves motor function",
            }
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            aligned = validate_triples(path, require_evidence_alignment=True)

            self.assertFalse(missing["valid"])
            self.assertTrue(aligned["valid"])


if __name__ == "__main__":
    unittest.main()
