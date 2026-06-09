import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.biomedical.confidence import normalize_and_score
from src.biomedical.schema import (
    has_conflicting_polarity,
    normalize_relation,
    normalize_triple,
)
from src.extraction.local_pipeline import rule_candidate_extraction
from src.extraction.merge_triples import merge_jsonl
from src.extraction.run_stage2_extraction import build_split


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
        positive = rule_candidate_extraction(
            "Nusinersen treatment improved motor function in SMA.", "1"
        )
        negative = rule_candidate_extraction(
            "Nusinersen did not improve motor function in SMA.", "2"
        )
        self.assertTrue(any(item["relation"] == "IMPROVES" for item in positive))
        self.assertTrue(all(item["extracted_by"] == "Rule_Candidate" for item in positive))
        self.assertEqual(negative, [])

    def test_conflicting_relation_polarity_is_detected(self):
        self.assertTrue(has_conflicting_polarity({"IMPROVES", "WORSENS"}))
        self.assertFalse(has_conflicting_polarity({"IMPROVES", "TREATS"}))

    def test_stage2_split_names_rule_candidates_not_regex_fallback(self):
        with TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "abstracts.jsonl"
            records = [
                {"pmid": "1", "abstract": "A"},
                {"pmid": "2", "abstract": "B"},
                {"pmid": "3", "abstract": "C"},
            ]
            input_file.write_text(
                "".join(json.dumps(item) + "\n" for item in records),
                encoding="utf-8",
            )
            split, _ = build_split(input_file, llm_limit=1, model="test-model", chunk_size=20)
            self.assertEqual(split["llm_pmids"], ["1"])
            self.assertEqual(split["rule_candidate_pmids"], ["2", "3"])
            self.assertNotIn("regex_pmids", split)

    def test_stage2_canonical_merge_can_exclude_rule_candidates(self):
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            llm_file = tmp_dir / "llm.jsonl"
            rule_file = tmp_dir / "rule_candidates.jsonl"
            canonical_file = tmp_dir / "extracted.jsonl"
            llm_record = {
                "source_pmid": "1",
                "entity_1": {"name": "Nusinersen", "type": "Drug"},
                "relation": "IMPROVES",
                "entity_2": {"name": "motor function", "type": "Phenotype"},
                "extracted_by": "LLM_test",
            }
            rule_record = {
                "source_pmid": "2",
                "entity_1": {"name": "SMN1", "type": "Gene"},
                "relation": "ASSOCIATED_WITH",
                "entity_2": {"name": "SMA", "type": "Disease"},
                "extracted_by": "Rule_Candidate",
            }
            llm_file.write_text(json.dumps(llm_record) + "\n", encoding="utf-8")
            rule_file.write_text(json.dumps(rule_record) + "\n", encoding="utf-8")

            merge_jsonl([str(llm_file)], str(canonical_file))

            merged = [json.loads(line) for line in canonical_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(merged, [llm_record])


if __name__ == "__main__":
    unittest.main()
