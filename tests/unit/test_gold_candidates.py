import unittest

from src.extraction.build_gold_candidates import (
    evaluation_challenge_candidates,
    evidence_exact_match,
    triple_signature,
)


def make_triple(index, relation="ASSOCIATED_WITH", confidence=0.95, evidence="supported text"):
    return {
        "source_pmid": str(index),
        "entity_1": {"name": f"Entity A {index}", "type": "Gene"},
        "relation": relation,
        "entity_2": {"name": f"Entity B {index}", "type": "Disease"},
        "evidence_text": evidence,
        "computed_confidence": confidence,
        "extracted_by": "LLM_test",
    }


class GoldCandidateSamplingTests(unittest.TestCase):
    def setUp(self):
        self.triples = [
            make_triple(index, "ASSOCIATED_WITH" if index % 2 else "TREATS", 0.75 if index < 5 else 0.95)
            for index in range(1, 31)
        ]
        self.abstracts = {
            str(index): {"title": "", "abstract": "This contains supported text."}
            for index in range(1, 31)
        }

    def test_evidence_exact_match_uses_source_text(self):
        self.assertTrue(evidence_exact_match(self.triples[0], self.abstracts))
        changed = {**self.triples[0], "evidence_text": "missing phrase"}
        self.assertFalse(evidence_exact_match(changed, self.abstracts))

    def test_evaluation_challenge_sample_is_deterministic_and_unique(self):
        first = evaluation_challenge_candidates(self.triples, self.abstracts, 20, 15, 42)
        second = evaluation_challenge_candidates(self.triples, self.abstracts, 20, 15, 42)

        self.assertEqual([triple_signature(item) for item in first], [triple_signature(item) for item in second])
        self.assertEqual(len(first), 20)
        self.assertEqual(len({triple_signature(item) for item in first}), 20)
        self.assertEqual(sum(item["sample_group"] == "primary_random" for item in first), 15)
        self.assertEqual(sum(item["sample_group"] == "challenge" for item in first), 5)
        self.assertEqual(sum(item["requires_second_review"] for item in first), 4)


if __name__ == "__main__":
    unittest.main()
