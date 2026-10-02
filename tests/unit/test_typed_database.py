import json
import unittest
from src.database.neo4j_importer import build_import_records


class TypedDatabaseTests(unittest.TestCase):
    def fixture(self):
        aligned = [{"entity_1": {"name": "SMN", "type": kind}, "relation": "ASSOCIATED_WITH",
                    "entity_2": {"name": "SMA", "type": "Disease"}, "source_pmid": str(i), "evidence_text": "Original quote."}
                   for i, kind in enumerate(("Gene", "Protein"), 1)]
        fused = [{"entity_1": row["entity_1"], "relation": row["relation"], "entity_2": row["entity_2"],
                  "evidence": {"evidence_count": 1, "pmid_list": [row["source_pmid"]]}, "computed_confidence": .8} for row in aligned]
        quality = [{"raw_record_number": i, "original_assertion": row, "quality": {"context_sentences": [], "flags": []}}
                   for i, row in enumerate(aligned, 1)]
        return fused, aligned, quality

    def test_same_name_different_types_preserve_nodes_and_assertions(self):
        fused, aligned, quality = self.fixture()
        nodes, edges = build_import_records(fused, [], aligned, quality, "test-v1")
        self.assertEqual(len(nodes), 3)
        self.assertEqual(len(edges), 2)
        self.assertNotEqual(edges[0]["a"], edges[1]["a"])
        self.assertEqual(sum(e["props"]["evidence_count"] for e in edges), 2)
        self.assertEqual(json.loads(edges[0]["props"]["assertion_records_json"])[0]["evidence_text"], "Original quote.")

    def test_external_and_literature_source_cannot_overwrite_same_relation(self):
        fused, aligned, quality = self.fixture()
        external = [{"gene_symbol": "SMN", "target_id": "ENSG-test", "disease_id": "MONDO-test", "score": .7}]
        nodes, edges = build_import_records(fused, external, aligned, quality, "test-v1")
        self.assertEqual(len(nodes), 5)
        self.assertEqual(len(edges), 3)
        self.assertEqual({e["props"]["source"] for e in edges}, {"Literature_NLP", "OpenTargets"})
        self.assertNotIn("evidence_pmids", edges[-1]["props"])

    def test_missing_or_changed_provenance_refuses_import(self):
        fused, aligned, quality = self.fixture()
        quality[0]["original_assertion"] = {**quality[0]["original_assertion"], "evidence_text": "Different quote"}
        with self.assertRaises(ValueError): build_import_records(fused, [], aligned, quality, "test-v1")

    def test_versioned_keys_do_not_collide_with_prior_graph(self):
        fused, aligned, quality = self.fixture()
        a, ae = build_import_records(fused, [], aligned, quality, "test-v1")
        b, be = build_import_records(fused, [], aligned, quality, "test-v2")
        self.assertFalse({n["entity_key"] for n in a} & {n["entity_key"] for n in b})
        self.assertFalse({e["props"]["edge_key"] for e in ae} & {e["props"]["edge_key"] for e in be})
