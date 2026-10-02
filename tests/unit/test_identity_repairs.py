import unittest
from src.biomedical.entity_identity import authority_ids, compatible_identity, entity_id
from src.fusion.dictionary_mapper import map_entity
from src.fusion.semantic_aligner import apply_alignment, build_alignment_map


def triple(first, second):
    return {"entity_1": first, "entity_2": second, "source_pmid": "1", "relation": "ASSOCIATED_WITH", "evidence_text": "unchanged"}


class IdentityRepairsTests(unittest.TestCase):
    def test_homologous_genes_and_qualifiers_are_not_identity(self):
        for a, b in [("SMN1", "SMN2"), ("SMN2", "SMN2 (Exon 7)"),
                     ("SMA type 2", "SMA type 3"), ("SMA", "SMA type II"),
                     ("SMN1 deletion", "SMN1")]:
            self.assertFalse(compatible_identity("Gene" if a.startswith("SMN") else "Disease", a, b))

    def test_dictionary_cannot_override_authority_or_drop_subtype(self):
        dictionary = {"gene": {"smn2": "SMN1"}, "disease": {"sma type iii": "SMA type 2", "sma1": "Spinal Muscular Atrophy Type 1"}}
        self.assertEqual(map_entity({"name": "SMN2", "type": "Gene"}, dictionary)["name"], "SMN2")
        self.assertEqual(map_entity({"name": "SMA type III", "type": "Disease"}, dictionary)["name"], "SMA type III")
        self.assertEqual(map_entity({"name": "SMA1", "type": "Disease"}, dictionary)["name"], "Spinal Muscular Atrophy Type 1")

    def test_shared_name_typed_frequency_and_lookup_remain_separate(self):
        gene = {"name": "SHARED", "type": "Gene"}
        protein = {"name": "shared", "type": "Protein"}
        records = [triple(gene, protein), triple({"name": "shared", "type": "Gene"}, protein)]
        records += [triple(gene, {"name": "SHARED", "type": "Protein"})]
        records += [triple(gene, protein)] * 3
        mapping = build_alignment_map(records)
        aligned = apply_alignment(records, mapping)
        self.assertEqual(aligned[1]["entity_1"]["name"], "SHARED")
        self.assertEqual(aligned[2]["entity_2"]["name"], "shared")
        self.assertEqual(records[1]["entity_1"]["name"], "shared")
        self.assertEqual(aligned[0]["evidence_text"], "unchanged")

    def test_no_semantic_or_transitive_identity_merge(self):
        records = [triple({"type": "Gene", "name": a}, {"type": "Disease", "name": "SMA"}) for a in ["SMN1", "SMN2", "SMN"]]
        self.assertEqual(apply_alignment(records, build_alignment_map(records)), records)

    def test_database_identity_is_typed_and_source_scoped(self):
        self.assertNotEqual(entity_id({"name": "SMN", "type": "Gene"}), entity_id({"name": "SMN", "type": "Protein"}))
        self.assertNotEqual(entity_id({"name": "SMN2", "type": "Gene"}), entity_id({"name": "ENSG00000205571", "type": "Gene"}, "opentargets"))
        self.assertEqual(authority_ids({"name": "SMN2", "type": "Gene"})["ncbi_gene"], "6607")
        self.assertFalse(authority_ids({"name": "SMN2", "type": "Protein"}))
        self.assertFalse(authority_ids({"name": "SMN2 (Exon 7)", "type": "Gene"}))
