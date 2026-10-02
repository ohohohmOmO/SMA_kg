import unittest
from src.biomedical.assertion_quality import screen_assertion
from src.evaluation.run_assertion_quality_evaluation import validate_model_decision


def record(span, etype="Drug", relation="IMPROVES", first="Nusinersen", second="motor function", second_type="Phenotype"):
    return {"entity_1": {"name": first, "type": etype}, "relation": relation,
            "entity_2": {"name": second, "type": second_type}, "evidence_text": span}


class AssertionQualityTests(unittest.TestCase):
    def test_decimal_statistics_do_not_truncate_sentence_or_source_offsets(self):
        text = "BACKGROUND: Preliminary observations. RESULTS: Nusinersen improved motor function in children (P < .05) compared with controls. CONCLUSION: More study is needed."
        result = screen_assertion(record("Nusinersen improved motor function"), {"abstract": text})
        context = result["context_sentences"][0]
        self.assertEqual(context["text"], "RESULTS: Nusinersen improved motor function in children (P < .05) compared with controls.")
        self.assertEqual(text[context["start"]:context["end"]], context["text"])
        self.assertIn("qualified_statement_requires_review", result["flags"])

    def test_full_sentence_carries_population_and_comparator_when_fragment_drops_it(self):
        source = {"abstract": "Nusinersen improved motor function only in treated mice compared with controls."}
        result = screen_assertion(record("Nusinersen improved motor function"), source)
        self.assertFalse(result["eligible_candidate"])
        self.assertEqual(result["context_sentences"][0]["text"], source["abstract"])
        self.assertIn("qualified_statement_requires_review", result["flags"])

    def test_gene_deletion_does_not_support_unqualified_gene_causation(self):
        text = "Deletion of SMN1 causes spinal muscular atrophy in affected infants."
        result = screen_assertion(record(text, "Gene", "CAUSES", "SMN1", "spinal muscular atrophy", "Disease"), {"abstract": text})
        self.assertIn("gene_perturbation_is_not_gene_itself", result["flags"])

    def test_valid_schema_type_can_still_be_wrong_type(self):
        text = "Nusinersen improved motor function during the observation period."
        result = screen_assertion(record(text, "Gene"), {"abstract": text})
        self.assertIn("entity_1:known_name_type_mismatch", result["flags"])

    def test_unqualified_screen_candidate_is_not_semantically_verified(self):
        text = "Nusinersen treatment significantly improved motor function overall."
        result = screen_assertion(record(text), {"abstract": text})
        self.assertTrue(result["eligible_candidate"])
        self.assertEqual(result["semantic_support"], "not_evaluated")

    def test_model_direct_cannot_override_wrong_type_or_lost_conditions(self):
        text = "Nusinersen treatment significantly improved motor function overall."
        decision = {"support": "direct", "entity_types_correct": True, "direction_correct": True, "conditions_preserved": True,
                    "source_field": "abstract", "evidence_quote": text, "missing_conditions": [], "reason": "Explicit statement"}
        self.assertTrue(validate_model_decision(decision, {"abstract": text})["model_screened_candidate"])
        for key in ("entity_types_correct", "direction_correct", "conditions_preserved"):
            self.assertFalse(validate_model_decision({**decision, key: False}, {"abstract": text})["model_screened_candidate"])
        self.assertFalse(validate_model_decision({**decision, "missing_conditions": ["mice"]}, {"abstract": text})["model_screened_candidate"])

    def test_fabricated_quote_and_exact_but_incomplete_quote_fail_closed(self):
        text = "Nusinersen treatment improved motor function only in mice."
        base = {"support": "direct", "entity_types_correct": True, "direction_correct": True, "conditions_preserved": True,
                "source_field": "abstract", "missing_conditions": [], "reason": "test"}
        for quote in ("Nusinersen treatment improved motor function", "Human trials established efficacy."):
            self.assertFalse(validate_model_decision({**base, "evidence_quote": quote}, {"abstract": text})["model_screened_candidate"])
