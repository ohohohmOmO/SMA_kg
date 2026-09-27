import unittest

from src.qa.claim_evidence_validation import (
    validate_answer_semantics,
    validate_claim_evidence,
)


def aligned_context():
    return {
        "aligned_triples": [
            {
                "evidence_id": "T001",
                "source_pmid": "1",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence_text": "Nusinersen treatment improved motor function in children with SMA.",
            }
        ],
        "fused_edges": [],
        "graph_neighborhood": [],
        "allowed_evidence_ids": ["T001"],
        "allowed_citation_pmids": ["1"],
    }


class ClaimEvidenceValidationTest(unittest.TestCase):
    def test_direct_triple_support_is_entailed(self):
        claim = {
            "claim_id": "C001",
            "claim_type": "treatment",
            "text": "Nusinersen improves motor function.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, aligned_context())

        self.assertEqual(result["label"], "entailed")
        self.assertTrue(result["passed"])
        self.assertTrue(result["critical"])

    def test_negated_claim_is_contradicted_by_positive_evidence(self):
        claim = {
            "claim_id": "C002",
            "claim_type": "treatment",
            "text": "Nusinersen does not improve motor function.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, aligned_context())

        self.assertEqual(result["label"], "contradicted")
        self.assertFalse(result["passed"])
        self.assertIn("negation_mismatch", result["violations"])

    def test_changed_dosage_is_contradicted(self):
        context = aligned_context()
        context["aligned_triples"][0]["evidence_text"] = (
            "Children received 12 mg nusinersen and improved motor function."
        )
        claim = {
            "claim_id": "C003",
            "claim_type": "dosage",
            "text": "Children received 50 mg nusinersen and improved motor function.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, context)

        self.assertEqual(result["label"], "contradicted")
        self.assertIn("numeric_mismatch", result["violations"])

    def test_opposite_relation_direction_is_contradicted(self):
        context = aligned_context()
        context["aligned_triples"][0]["relation"] = "WORSENS"
        context["aligned_triples"][0]["evidence_text"] = (
            "Nusinersen worsened motor function in the reported cohort."
        )
        claim = {
            "claim_id": "C004",
            "claim_type": "treatment",
            "text": "Nusinersen improves motor function.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, context)

        self.assertEqual(result["label"], "contradicted")
        self.assertIn("relation_polarity_mismatch", result["violations"])

    def test_population_change_is_insufficient(self):
        context = aligned_context()
        context["aligned_triples"][0]["evidence_text"] = (
            "Nusinersen improved motor function in adults with SMA."
        )
        claim = {
            "claim_id": "C005",
            "claim_type": "treatment",
            "text": "Nusinersen improves motor function in infants with SMA.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, context)

        self.assertEqual(result["label"], "insufficient")
        self.assertIn("population_mismatch", result["violations"])

    def test_unrelated_entities_are_classified_as_unrelated(self):
        claim = {
            "claim_id": "C006",
            "claim_type": "diagnosis",
            "text": "MRI diagnoses scoliosis.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, aligned_context())

        self.assertEqual(result["label"], "unrelated")
        self.assertIn("entity_mismatch", result["violations"])

    def test_uncertain_paraphrase_can_be_resolved_by_entailment_judge(self):
        claim = {
            "claim_id": "C007",
            "claim_type": "treatment",
            "text": "Nusinersen supported better motor function.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        def judge(**_kwargs):
            return {
                "label": "entailed",
                "score": 0.94,
                "matched_quote": "Nusinersen treatment improved motor function",
                "reason": "The source directly supports the claim.",
            }

        result = validate_claim_evidence(claim, aligned_context(), judge=judge)

        self.assertEqual(result["label"], "entailed")
        self.assertEqual(result["evidence_results"][0]["method"], "llm_judge")

    def test_critical_unsupported_claim_fails_the_whole_answer(self):
        supported = {
            "claim_id": "C001",
            "claim_type": "treatment",
            "text": "Nusinersen improves motor function.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }
        unsupported = {
            "claim_id": "C002",
            "claim_type": "contraindication",
            "text": "Nusinersen is contraindicated in adults.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_answer_semantics(
            {"claims": [supported, unsupported]},
            aligned_context(),
            mode="enforce",
        )

        self.assertFalse(result["passed"])
        self.assertIn("critical_claim_not_entailed:C002", result["violations"])

    def test_criticality_is_inferred_when_model_omits_claim_type(self):
        claim = {
            "claim_id": "C008",
            "text": "Patients should receive 50 mg nusinersen.",
            "supporting_pmids": ["1"],
            "supporting_evidence_ids": ["T001"],
        }

        result = validate_claim_evidence(claim, aligned_context())

        self.assertTrue(result["critical"])
        self.assertEqual(result["claim_type"], "dosage")

    def test_conflicting_cited_evidence_does_not_pass_as_entailed(self):
        context = aligned_context()
        context["aligned_triples"].append(
            {
                "evidence_id": "T002",
                "source_pmid": "2",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "WORSENS",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence_text": "Nusinersen worsened motor function.",
            }
        )
        context["allowed_evidence_ids"].append("T002")
        context["allowed_citation_pmids"].append("2")
        claim = {
            "claim_id": "C009",
            "claim_type": "treatment",
            "text": "Nusinersen improves motor function.",
            "supporting_pmids": ["1", "2"],
            "supporting_evidence_ids": ["T001", "T002"],
        }

        result = validate_claim_evidence(claim, context)

        self.assertEqual(result["label"], "contradicted")
        self.assertIn("conflicting_cited_evidence", result["violations"])


if __name__ == "__main__":
    unittest.main()
