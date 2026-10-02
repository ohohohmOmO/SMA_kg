# Resolve typed graph versus name-only database identity

Status: closed

The literature snapshot has 6,684 (name,type) nodes but 6,524 names. Existing
Neo4jImporter constrains and merges Entity.name only, so cross-type identically
named entities share nodes/labels. The evaluation records this mismatch without
changing live data. Some differences may reflect ambiguous extraction typing,
so a schema and annotation decision should precede migration.

Acceptance: specify typed identifiers versus permitted multi-type entities,
preserve provenance, test shared Gene/Protein names and Open Targets integration,
provide a reversible migration and validated count reconciliation. No implicit
database clearing or unreviewed biomedical reinterpretation.

## Resolution 2026-10-02

Versioned typed/source identity implemented; all node/relationship/evidence properties reconciled online. Active typed-v2-8a4dbccd4fdc22ca has9,218 nodes/13,165 edges. Legacy counts/constraints preserved; no deletion. Shared Gene/Protein and source overwrite regression tests pass.

Evidence: `docs/reproduction/FYP_FOUR_REPAIRS_2026-10-02.md`.
