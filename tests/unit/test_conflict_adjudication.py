import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.fusion.adjudicate_relation_conflicts import (
    build_payload,
    insufficient_evidence_adjudication,
    main,
    validate_adjudication,
)
from src.fusion.prepare_conflict_adjudication_review import build_review_proposal


def write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


class ConflictAdjudicationTest(unittest.TestCase):
    def test_validate_adjudication_requires_known_decision_and_context_pmids(self):
        payload = {
            "conflict_id": "SMA-CONFLICT-0001",
            "evidence_context": {"supporting_pmids": ["1"]},
        }
        valid = {
            "decision": "insufficient_evidence",
            "retained_relations": [],
            "rejected_relations": [],
            "confidence": 0.0,
            "supporting_pmids": ["1"],
        }
        invalid = {**valid, "decision": "made_up", "supporting_pmids": ["2"]}

        self.assertEqual(validate_adjudication(valid, payload), [])
        self.assertIn("decision_invalid", validate_adjudication(invalid, payload))
        self.assertIn("supporting_pmid_not_in_context", validate_adjudication(invalid, payload))

    def test_insufficient_evidence_adjudication_is_schema_complete(self):
        payload = {
            "conflict_id": "SMA-CONFLICT-0001",
            "entity_1": {"name": "A"},
            "entity_2": {"name": "B"},
            "conflicting_relations": ["ASSOCIATED_WITH"],
        }

        record = insufficient_evidence_adjudication(payload)

        self.assertEqual(record["decision"], "insufficient_evidence")
        self.assertEqual(record["review_status"], "unresolved")
        self.assertEqual(record["supporting_pmids"], [])

    def test_dry_run_writes_payloads_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            abstracts = root / "abstracts.jsonl"
            aligned = root / "aligned.jsonl"
            fused = root / "fused.jsonl"
            conflicts = root / "conflicts.jsonl"
            run_dir = root / "run"
            e1 = {"name": "Nusinersen", "type": "Drug"}
            e2 = {"name": "motor function", "type": "Phenotype"}
            conflict = {"entity_1": e1, "entity_2": e2, "relations": ["IMPROVES"]}
            write_jsonl(abstracts, [{"pmid": "1", "title": "t", "abstract": "Nusinersen improves motor function."}])
            write_jsonl(aligned, [{"source_pmid": "1", "entity_1": e1, "relation": "IMPROVES", "entity_2": e2}])
            write_jsonl(fused, [{"entity_1": e1, "relation": "IMPROVES", "entity_2": e2, "evidence": {"pmid_list": ["1"]}}])
            write_jsonl(conflicts, [conflict])

            argv = [
                "adjudicate_relation_conflicts.py",
                "--dry-run",
                "--conflicts-file",
                str(conflicts),
                "--abstracts-file",
                str(abstracts),
                "--aligned-file",
                str(aligned),
                "--fused-file",
                str(fused),
                "--run-dir",
                str(run_dir),
            ]
            with patch.object(sys, "argv", argv):
                self.assertEqual(main(), 0)

            payloads = (run_dir / "payloads.jsonl").read_text(encoding="utf-8").strip().splitlines()
            summary = json.loads((run_dir / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payloads), 1)
            self.assertTrue(summary["valid"])
            self.assertEqual(summary["mode"], "dry_run")
            self.assertTrue((run_dir / "manifest.csv").exists())

    def test_build_payload_preserves_conflict_metadata(self):
        conflict = {
            "entity_1": {"name": "A"},
            "entity_2": {"name": "B"},
            "relations": ["X", "Y"],
            "reason": "test",
        }
        context = {"context_id": "cid", "supporting_pmids": []}

        payload = build_payload(context, conflict, 3)

        self.assertEqual(payload["conflict_id"], "cid")
        self.assertEqual(payload["conflict_index"], 3)
        self.assertEqual(payload["conflicting_relations"], ["X", "Y"])

    def test_review_proposal_requires_human_approval_before_promotion(self):
        adjudication = {
            "conflict_id": "SMA-CONFLICT-0001",
            "entity_1": {"name": "A"},
            "entity_2": {"name": "B"},
            "conflicting_relations": ["DECREASES", "PREVENTS"],
            "decision": "relation_normalization_issue",
            "retained_relations": ["PREVENTS"],
            "rejected_relations": ["DECREASES"],
            "supporting_pmids": ["1"],
            "confidence": 0.95,
            "rationale": "Normalize relation polarity.",
        }

        proposal = build_review_proposal(adjudication)

        self.assertEqual(proposal["promotion_action"], "propose_relation_updates")
        self.assertEqual(proposal["retain_relations_after_review"], ["PREVENTS"])
        self.assertTrue(proposal["requires_human_approval"])
        self.assertFalse(proposal["canonical_graph_mutated"])


if __name__ == "__main__":
    unittest.main()
