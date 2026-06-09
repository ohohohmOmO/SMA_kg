import unittest

from src.biomedical.confidence import normalize_and_score
from src.biomedical.schema import (
    has_conflicting_polarity,
    normalize_relation,
    normalize_triple,
)
from src.extraction.local_pipeline import regex_fallback_extraction


class BiomedicalQualityTests(unittest.TestCase):
    def test_relation_aliases_normalize_to_canonical_relations(self):
        self.assertEqual(normalize_relation("TREATS_MENTION"), "TREATS")
        self.assertEqual(normalize_relation("treated_with"), "TREATS")
        self.assertEqual(normalize_relation("CO-OCCURS_WITH"), "CO_OCCURS_WITH")

    def test_invalid_entity_type_is_rejected(self):
        _, problems = normalize_triple(
            {
                "source_pmid": "1",
                "entity_1": {"name": "SMA patient", "type": "Patient"},
                "relation": "ASSOCIATED_WITH",
                "entity_2": {"name": "SMA", "type": "Disease"},
            }
        )
        self.assertIn("entity_1.type_invalid", problems)

    def test_confidence_is_component_based_not_fixed_literal(self):
        normalized, problems = normalize_and_score(
            {
                "source_pmid": "1",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence_text": "Nusinersen improved motor function.",
                "llm_confidence": 0.83,
                "extracted_by": "LLM_deepseek-ai/DeepSeek-V4-Flash",
            },
            require_evidence=True,
        )
        self.assertFalse(problems)
        self.assertNotEqual(normalized["computed_confidence"], 0.9)
        self.assertIn("confidence_components", normalized)

    def test_local_rule_extraction_uses_sentence_evidence_and_negation_filter(self):
        positive = regex_fallback_extraction(
            "Nusinersen treatment improved motor function in SMA.", "1"
        )
        negative = regex_fallback_extraction(
            "Nusinersen did not improve motor function in SMA.", "2"
        )
        self.assertTrue(any(item["relation"] == "IMPROVES" for item in positive))
        self.assertEqual(negative, [])

    def test_conflicting_relation_polarity_is_detected(self):
        self.assertTrue(has_conflicting_polarity({"IMPROVES", "WORSENS"}))
        self.assertFalse(has_conflicting_polarity({"IMPROVES", "TREATS"}))


if __name__ == "__main__":
    unittest.main()
