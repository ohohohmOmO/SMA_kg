import unittest

from src.evaluation.claim_evidence_silver import (
    build_silver_cases,
    evaluate_silver_cases,
)


class ClaimEvidenceSilverTest(unittest.TestCase):
    def test_silver_cases_cover_rule_mutations_and_regress_cleanly(self):
        records = [
            {
                "source_pmid": "1",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence_text": (
                    "Children received 12 mg nusinersen and improved motor function."
                ),
            }
        ]

        cases = build_silver_cases(records, limit=1)
        summary = evaluate_silver_cases(cases)

        methods = {case["generation_method"] for case in cases}
        self.assertTrue(
            {
                "triple_positive",
                "negation_flip",
                "relation_polarity_flip",
                "numeric_change",
                "population_change",
                "unrelated_entities",
            }.issubset(methods)
        )
        self.assertEqual(summary["mismatches"], 0)
        self.assertEqual(summary["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
