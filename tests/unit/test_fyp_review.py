import unittest

from src.evaluation.audit_fyp_inputs import locate_evidence
from src.evaluation.summarize_gold_review import summarize_reviews


def reviewed(label="2", group="primary_random", **updates):
    row = {"candidate_id": "sample", "sample_group": group, "requires_second_review": "no",
           "review_status": "completed", "support_label": label, "reviewer_id": "R1", "review_date": "2026-10-02",
           "entity_1_correct": "yes", "entity_2_correct": "yes", "relation_correct": "yes",
           "direction_correct": "yes", "evidence_span_correct": "yes", "error_type": "no_error",
           "review_notes": "Synthetic example used only in tests."}
    row.update(updates)
    return row


class FypReviewTests(unittest.TestCase):
    def test_empty_review_is_pending_not_zero_accuracy(self):
        report = summarize_reviews([{"sample_group": "primary_random", "review_status": "pending_review"}])
        self.assertIsNone(report["groups"]["primary_random"]["metrics"])
        self.assertEqual(report["validation_issues"], [])

    def test_unknowns_and_challenge_are_not_silently_pooled(self):
        rows = [reviewed(), reviewed("U", candidate_id="unknown"), reviewed("0", "challenge", candidate_id="challenge")]
        report = summarize_reviews(rows)
        main = report["groups"]["primary_random"]["metrics"]
        self.assertEqual(main["resolved_denominator"], 1)
        self.assertEqual(main["unknown_fraction_all_samples"], 0.5)
        self.assertEqual(main["strict_confirmed_fraction_all_samples"], 0.5)
        self.assertEqual(main["strict_support_bounds_if_unknowns_resolve"], [0.5, 1.0])
        self.assertEqual(report["groups"]["challenge"]["metrics"]["strict_support_rate_among_resolved"], 0)

    def test_disagreement_blocks_final_rates_until_adjudicated(self):
        row = reviewed(requires_second_review="yes", second_support_label="0", second_reviewer_id="R2", second_review_date="2026-10-03")
        self.assertIsNone(summarize_reviews([row])["groups"]["primary_random"]["metrics"])
        row.update(adjudicated_label="0", adjudication_notes="R1 and R2, 2026-10-04: source contradicts the prediction.")
        result = summarize_reviews([row])
        self.assertEqual(result["groups"]["primary_random"]["metrics"]["strict_support_rate_among_resolved"], 0)
        self.assertEqual(result["agreement_before_adjudication"]["raw_agreement"], 0)

    def test_missing_identity_or_self_second_review_blocks_metrics(self):
        row = reviewed(reviewer_id="")
        self.assertTrue(summarize_reviews([row])["validation_issues"])
        row = reviewed(requires_second_review="yes", second_support_label="2", second_reviewer_id="R1", second_review_date="2026-10-03")
        report = summarize_reviews([row])
        self.assertTrue(report["validation_issues"])
        self.assertIsNone(report["groups"]["primary_random"]["metrics"])

    def test_correct_relation_can_have_inadequate_extracted_evidence(self):
        row = reviewed(evidence_span_correct="no", error_type="insufficient_evidence")
        report = summarize_reviews([row])
        self.assertEqual(report["validation_issues"], [])
        self.assertEqual(report["groups"]["primary_random"]["metrics"]["strict_support_rate_among_resolved"], 1)

    def test_span_match_is_only_text_location(self):
        source = {"1": {"title": "A title", "abstract": "Drug A did not improve outcome B."}}
        record = {"source_pmid": "1", "evidence_text": "Drug A did not improve outcome B."}
        self.assertEqual(locate_evidence(record, source), "exact")
        self.assertEqual(locate_evidence({**record, "evidence_text": "drug a  did not improve outcome B."}, source), "case_whitespace_match")
        self.assertEqual(locate_evidence({**record, "evidence_text": "Drug A improved outcome B."}, source), "not_located")
        self.assertEqual(locate_evidence({**record, "source_pmid": "missing"}, source), "missing_source")


if __name__ == "__main__":
    unittest.main()
