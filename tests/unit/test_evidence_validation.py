import unittest

from src.biomedical.evidence_validation import contains_form, locate_span, validate_evidence


def triple(span):
    return {"entity_1": {"name": "Agent A", "type": "Drug"},
            "entity_2": {"name": "outcome B", "type": "Phenotype"},
            "relation": "DECREASES", "evidence_text": span}


class EvidenceValidationTests(unittest.TestCase):
    def test_typographic_normalization_returns_original_offsets(self):
        text = "Prefix. Agent A\u00a0\u00a0reduced outcome B\u2014significantly."
        result = locate_span("agent a reduced outcome b-significantly.", {"abstract": text})
        self.assertEqual(result["status"], "normalized")
        segment = result["segments"][0]
        self.assertEqual(text[segment["start"]:segment["end"]], segment["text"])
        self.assertIn("\u00a0", segment["text"])

    def test_ellipsis_order_and_same_field_are_required(self):
        text = "Agent A was studied. A trial reduced outcome B."
        result = locate_span("Agent A ... reduced outcome B", {"abstract": text})
        self.assertEqual(result["status"], "ordered_fragments")
        self.assertEqual(len(result["segments"]), 2)
        reverse = locate_span("reduced outcome B ... Agent A", {"abstract": text}, False)
        self.assertEqual(reverse["status"], "not_located")
        cross_fields = locate_span("Agent A ... reduced outcome B", {"title": "Agent A", "abstract": "reduced outcome B"}, False)
        self.assertEqual(cross_fields["status"], "not_located")

    def test_fuzzy_suggestion_never_counts_as_traceable(self):
        source = {"abstract": "Agent A has clearly reduced outcome B in this trial."}
        span = "Agent A has clearly reduces outcome B in this trial."
        result = validate_evidence(triple(span), source)
        self.assertIsNotNone(result["suggestion"])
        self.assertFalse(result["traceable"])
        self.assertFalse(result["eligible_span"])

    def test_exact_short_fragment_is_not_adequate_candidate(self):
        source = {"abstract": "Agent A significantly reduced outcome B in this trial."}
        result = validate_evidence(triple("outcome B"), source)
        self.assertTrue(result["traceable"])
        self.assertFalse(result["eligible_span"])
        self.assertIn("missing_endpoint_in_span", result["flags"])

    def test_context_negation_routes_positive_fragment_for_review(self):
        source = {"abstract": "There was no evidence that Agent A reduced outcome B in this trial."}
        result = validate_evidence(triple("Agent A reduced outcome B in this trial"), source)
        self.assertTrue(result["traceable"])
        self.assertIn("negation_requires_review", result["flags"])
        self.assertFalse(result["eligible_span"])

    def test_uncertainty_and_experimental_scope_are_not_silently_accepted(self):
        text = "Agent A may reduce outcome B in mice."
        result = validate_evidence(triple(text), {"abstract": text})
        self.assertIn("uncertainty_requires_review", result["flags"])
        self.assertIn("experimental_context_requires_review", result["flags"])

    def test_lexical_eligibility_does_not_claim_entailment(self):
        text = "Agent A significantly reduced outcome B in this trial."
        result = validate_evidence(triple(text), {"abstract": text})
        self.assertTrue(result["eligible_span"])
        self.assertEqual(result["semantic_support"], "not_evaluated")

    def test_aliases_are_type_specific_and_token_boundaries_are_respected(self):
        dictionary = {"drug": {"a medicine": "Agent A"}}
        text = "A medicine significantly reduced outcome B in this trial."
        result = validate_evidence(triple(text), {"abstract": text}, dictionary)
        self.assertTrue(result["eligible_span"])
        self.assertFalse(contains_form("SMAX", ["sma"]))

    def test_missing_source_does_not_become_success(self):
        self.assertEqual(validate_evidence(triple("anything"), None)["location_status"], "missing_source")
        self.assertEqual(locate_span("", {"abstract": "anything"})["status"], "missing_evidence")


if __name__ == "__main__":
    unittest.main()
