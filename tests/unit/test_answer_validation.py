import json
import os
import unittest
from unittest.mock import patch

from src.qa.answer import generate_answer
from src.qa.answer_validation import (
    build_safe_fallback_answer,
    build_validated_answer,
    validate_answer_payload,
)


def build_context(with_conflict=False):
    return {
        "aligned_triples": [
            {
                "evidence_id": "T001",
                "source_pmid": "1",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence_text": "Nusinersen improved motor function.",
            }
        ],
        "fused_edges": [
            {
                "evidence_id": "F001",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "evidence": {"pmid_list": ["1", "2"]},
            }
        ],
        "graph_neighborhood": [],
        "conflicts": [{"conflict_id": "C001"}] if with_conflict else [],
        "supporting_pmids": ["1", "2"],
        "allowed_citation_pmids": ["1", "2"],
        "allowed_evidence_ids": ["T001", "F001"],
        "retrieval": {"mode": "test"},
    }


def valid_payload():
    return {
        "claims": [
            {
                "claim_id": "C001",
                "text": "Nusinersen improves motor function.",
                "supporting_pmids": ["1"],
                "supporting_evidence_ids": ["T001"],
            }
        ],
        "limitations": [],
        "confidence": 0.9,
    }


class AnswerValidationTest(unittest.TestCase):
    def test_valid_claim_passes_and_final_pmids_are_derived(self):
        context = build_context()
        payload = valid_payload()

        self.assertEqual(validate_answer_payload(payload, context), [])
        answer = build_validated_answer("question", payload, context, "model", 1)

        self.assertEqual(answer["answer_status"], "validated")
        self.assertEqual(answer["supporting_pmids"], ["1"])
        self.assertEqual(answer["supporting_triples"][0]["evidence_id"], "T001")
        self.assertTrue(answer["validation"]["passed"])

    def test_unauthorized_pmid_and_unknown_evidence_are_rejected(self):
        context = build_context()
        payload = valid_payload()
        payload["claims"][0]["supporting_pmids"] = ["999"]
        payload["claims"][0]["supporting_evidence_ids"] = ["T999"]

        problems = validate_answer_payload(payload, context)

        self.assertTrue(any(problem.startswith("claim_1_pmid_not_allowed") for problem in problems))
        self.assertTrue(any(problem.startswith("claim_1_evidence_id_not_allowed") for problem in problems))

    def test_pmid_must_belong_to_referenced_evidence(self):
        context = build_context()
        payload = valid_payload()
        payload["claims"][0]["supporting_pmids"] = ["2"]
        payload["claims"][0]["supporting_evidence_ids"] = ["T001"]

        problems = validate_answer_payload(payload, context)

        self.assertIn("claim_1_evidence_pmid_mismatch:T001", problems)
        self.assertIn("claim_1_pmid_not_backed_by_evidence:2", problems)

    def test_conflict_requires_a_limitation(self):
        context = build_context(with_conflict=True)

        self.assertIn("conflict_not_disclosed", validate_answer_payload(valid_payload(), context))

    def test_empty_claims_require_a_limitation(self):
        payload = {"claims": [], "limitations": [], "confidence": 0.0}

        self.assertIn("empty_answer_without_limitation", validate_answer_payload(payload, build_context()))

    @patch("src.qa.answer.build_client", return_value=object())
    @patch("src.qa.answer.call_llm")
    def test_generate_answer_retries_validation_and_accepts_correction(self, call_llm, _build_client):
        invalid = valid_payload()
        invalid["claims"][0]["supporting_pmids"] = ["999"]
        call_llm.side_effect = [
            json.dumps(invalid),
            json.dumps(valid_payload()),
        ]

        with patch.dict(os.environ, {"SILICONFLOW_API_KEY": "test"}, clear=False):
            answer = generate_answer("question", build_context(), model="test-model", validation_attempts=2)

        self.assertEqual(call_llm.call_count, 2)
        self.assertEqual(answer["answer_status"], "validated")
        self.assertEqual(answer["validation"]["attempts"], 2)
        self.assertTrue(call_llm.call_args.kwargs["validation_errors"])

    @patch("src.qa.answer.build_client", return_value=object())
    @patch("src.qa.answer.call_llm")
    def test_generate_answer_falls_back_after_repeated_invalid_output(self, call_llm, _build_client):
        call_llm.return_value = "{not-json"

        with patch.dict(os.environ, {"SILICONFLOW_API_KEY": "test"}, clear=False):
            answer = generate_answer("question", build_context(), model="test-model", validation_attempts=2)

        self.assertEqual(call_llm.call_count, 2)
        self.assertEqual(answer["answer_status"], "insufficient_or_invalid_evidence")
        self.assertEqual(answer["supporting_pmids"], [])
        self.assertFalse(answer["validation"]["passed"])
        self.assertEqual(answer["validation"]["violations"], ["answer_json_invalid"])

    def test_safe_fallback_never_exposes_unvalidated_evidence(self):
        answer = build_safe_fallback_answer("question", build_context(), "model", 2, ["bad"])

        self.assertEqual(answer["claims"], [])
        self.assertEqual(answer["supporting_pmids"], [])
        self.assertEqual(answer["supporting_triples"], [])

    @patch("src.qa.answer.build_client", return_value=object())
    @patch("src.qa.answer.call_llm")
    def test_semantically_unsupported_critical_claim_falls_back(self, call_llm, _build_client):
        payload = valid_payload()
        payload["claims"][0]["claim_type"] = "contraindication"
        payload["claims"][0]["text"] = "Nusinersen is contraindicated in adults."
        call_llm.return_value = json.dumps(payload)

        with patch.dict(os.environ, {"SILICONFLOW_API_KEY": "test"}, clear=False):
            answer = generate_answer(
                "question",
                build_context(),
                model="test-model",
                validation_attempts=2,
            )

        self.assertEqual(answer["answer_status"], "insufficient_or_invalid_evidence")
        self.assertFalse(answer["validation"]["passed"])
        self.assertTrue(
            any(
                item.startswith("critical_claim_not_entailed")
                for item in answer["validation"]["violations"]
            )
        )

    @patch("src.qa.answer.build_client", return_value=object())
    @patch("src.qa.answer.call_llm")
    def test_audit_mode_reports_semantic_failure_without_blocking(self, call_llm, _build_client):
        payload = valid_payload()
        payload["claims"][0]["claim_type"] = "contraindication"
        payload["claims"][0]["text"] = "Nusinersen is contraindicated in adults."
        call_llm.return_value = json.dumps(payload)

        with patch.dict(os.environ, {"SILICONFLOW_API_KEY": "test"}, clear=False):
            answer = generate_answer(
                "question",
                build_context(),
                model="test-model",
                semantic_validation_mode="audit",
            )

        self.assertEqual(answer["answer_status"], "validated")
        self.assertFalse(answer["validation"]["semantic"]["semantic_passed"])


if __name__ == "__main__":
    unittest.main()
