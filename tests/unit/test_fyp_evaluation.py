import unittest
from unittest.mock import patch

from src.evaluation.fyp_dataset import classify_gate, pmid_split, read_review_dataset, support_statistics
from src.evaluation.run_fyp_evaluation import graph_metrics
from src.evaluation.summarize_fusion_review import summarize as summarize_fusion


class FypEvaluationTests(unittest.TestCase):
    def test_relation_labels_and_span_labels_remain_separate(self):
        rows = [{"candidate_id": "1", "source_pmid": "a", "support_label": "2", "span_label": "no"},
                {"candidate_id": "2", "source_pmid": "b", "support_label": "0", "span_label": "yes"}]
        result = classify_gate(rows, {"1": False, "2": True})
        self.assertEqual(result["span_positive_predictive_value"], 1)
        self.assertEqual(result["strict_support_among_retained"], 0)
        self.assertEqual(result["strict_supported_candidates_retained"], 0)

    def test_unknowns_and_empty_acceptance_are_explicit(self):
        rows = [{"candidate_id": "1", "source_pmid": "a", "support_label": "U", "span_label": "unclear"}]
        stats = support_statistics(rows)
        self.assertIsNone(stats["strict_support"])
        self.assertEqual(stats["strict_all_sample_bounds"], [0, 1])
        gate = classify_gate(rows, {"1": False})
        self.assertIsNone(gate["span_positive_predictive_value"])
        self.assertIsNone(gate["adequate_span_sensitivity"])
        self.assertEqual(gate["unknown_span_labels"], 1)

    def test_source_split_never_leaks_pmids_between_groups(self):
        rows = [{"candidate_id": "SMA-RE-0001", "source_pmid": "same"},
                {"candidate_id": "later", "source_pmid": "same"},
                {"candidate_id": "other", "source_pmid": "other"}]
        split = pmid_split(rows)
        self.assertEqual(split["later"], "development")
        self.assertEqual(split["SMA-RE-0001"], split["later"])

    def test_graph_keeps_type_and_relation_identity(self):
        def edge(at, relation):
            return {"entity_1": {"name": "X", "type": at}, "relation": relation,
                    "entity_2": {"name": "Y", "type": "Disease"}}
        result = graph_metrics([edge("Gene", "ASSOCIATED_WITH"), edge("Gene", "CAUSES"), edge("Protein", "CAUSES")])
        self.assertEqual(result["typed_nodes"], 3)
        self.assertEqual(result["unique_relation_edges"], 3)
        self.assertEqual(result["unique_directed_pairs"], 2)

    def test_integrated_labels_do_not_invent_component_labels(self):
        row = {"candidate_id": "1", "review_status": "completed", "support_label": "2",
               "evidence_span_correct": "不合格", "reviewer_id": "model", "review_date": "2026-10-02",
               "review_notes": "short evidence", "entity_1_correct": ""}
        with patch("src.evaluation.fyp_dataset.read_annotation_workbook", return_value=[row]), \
             patch("src.evaluation.fyp_dataset.load_jsonl", return_value=([dict(row)], [])):
            rows, audit = read_review_dataset("fixture.xlsx", "fixture.jsonl")
        self.assertEqual(rows[0]["span_label"], "no")
        self.assertEqual(rows[0]["entity_1_correct"], "")
        self.assertEqual(audit["independent_second_reviews"], 0)

    def test_protected_inputs_fail_closed(self):
        with patch("src.evaluation.fyp_dataset.read_annotation_workbook", return_value=[{"candidate_id": "1", "relation": "CAUSES"}]), \
             patch("src.evaluation.fyp_dataset.load_jsonl", return_value=([{"candidate_id": "1", "relation": "TREATS"}], [])):
            with self.assertRaisesRegex(ValueError, "Protected"):
                read_review_dataset("fixture.xlsx", "fixture.jsonl")

    def test_fusion_missing_reviews_never_get_quality_metrics(self):
        queue = [{"review_id": "fixture", "entity_type": "Gene", "raw_name": "Alias",
                  "dictionary_name": "Alias", "aligned_name": "Canonical"}]
        result = summarize_fusion(queue, [])
        self.assertFalse(result["completed"])
        self.assertIsNone(result["stages"]["semantic"]["correct_among_resolved"])

    def test_fusion_unchanged_step_is_not_a_positive_semantic_label(self):
        original = {"review_id": "fixture", "entity_type": "Gene", "raw_name": "Alias",
                    "dictionary_name": "Alias", "aligned_name": "Canonical"}
        submitted = {**original, "dictionary_judgment": "not_changed", "semantic_judgment": "different",
                     "reviewer_id": "SyntheticTestReviewer", "review_date": "2026-10-02", "notes": "Synthetic distinct entities."}
        result = summarize_fusion([original], [submitted])
        self.assertTrue(result["completed"])
        self.assertIsNone(result["stages"]["dictionary"]["correct_among_resolved"])
        self.assertEqual(result["stages"]["semantic"]["correct_among_resolved"], 0)
        submitted["aligned_name"] = "Changed protected input"
        with self.assertRaisesRegex(ValueError, "Protected"):
            summarize_fusion([original], [submitted])

    def test_fusion_changed_step_cannot_be_bypassed_as_not_changed(self):
        original = {"review_id": "fixture", "entity_type": "Gene", "raw_name": "Alias",
                    "dictionary_name": "Alias", "aligned_name": "Canonical"}
        submitted = {**original, "dictionary_judgment": "not_changed", "semantic_judgment": "not_changed",
                     "reviewer_id": "SyntheticTestReviewer", "review_date": "2026-10-02"}
        with self.assertRaisesRegex(ValueError, "Invalid semantic"):
            summarize_fusion([original], [submitted])


if __name__ == "__main__":
    unittest.main()
