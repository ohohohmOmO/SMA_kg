import unittest

from src.evaluation.build_fyp_graph_explorer import assemble


class GraphSourceJoinTests(unittest.TestCase):
    def fixtures(self):
        raw = [{"entity_1": {"name": "SMN1", "type": "Gene"}, "relation": "ASSOCIATED_WITH",
                "entity_2": {"name": "SMA", "type": "Disease"}, "source_pmid": "1", "evidence_text": "SMN1 is associated with SMA."}]
        fused = [{**{k: raw[0][k] for k in ("entity_1", "entity_2", "relation")},
                  "evidence": {"pmid_list": ["1"], "evidence_count": 1}, "review_status": "needs_review"}]
        validations = [{"raw_record_number": 1, "source_pmid": "1",
                        "triple": {k: raw[0][k] for k in ("entity_1", "relation", "entity_2")},
                        "validation": {"location_status": "exact"}}]
        external = [{"gene_symbol": "SMN1", "target_id": "ENSG1", "disease_id": "MONDO1", "score": .7}]
        return raw, raw, fused, {"1": {"abstract": raw[0]["evidence_text"]}}, validations, external

    def test_full_source_join_preserves_original_and_separates_external(self):
        data = assemble(*self.fixtures())
        self.assertEqual(data["edges"][0]["records"][0]["pmid"], "1")
        self.assertTrue(data["edges"][0]["needs_review"])
        self.assertNotEqual(data["edges"][0]["a"], data["edges"][1]["a"])
        self.assertNotIn("pmids", data["edges"][1])

    def test_source_identity_mismatch_rejected(self):
        values = self.fixtures()
        values[4][0]["source_pmid"] = "wrong"
        with self.assertRaises(ValueError):
            assemble(*values)

    def test_missing_abstract_rejected(self):
        values = list(self.fixtures())
        values[3] = {}
        with self.assertRaises(ValueError):
            assemble(*values)

    def test_missing_fused_groups_rejected(self):
        values = list(self.fixtures())
        values[2] = []
        with self.assertRaises(ValueError):
            assemble(*values)


if __name__ == "__main__":
    unittest.main()
