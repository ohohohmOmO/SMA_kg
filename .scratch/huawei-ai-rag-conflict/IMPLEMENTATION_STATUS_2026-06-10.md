# Implementation Status - 2026-06-10

Feature scope:

- SMA Graph RAG intelligent question answering.
- Relation-conflict automatic adjudication.

Status: v1 implemented and locally verified.

Completed:

- Evidence Context builder over local PubMed abstracts, aligned triples, fused
  edges, and conflict records.
- Conflict adjudication CLI with dry-run payload generation and live LLM mode.
- Graph RAG retrieval CLI with lexical/entity retrieval and bounded evidence
  contexts.
- Graph RAG answer CLI with dry-run evidence packages and live LLM mode.
- Manifest-only Graph RAG index over canonical JSONL inputs.
- Unit tests for evidence context, conflict adjudication schema/dry-run, and
  Graph RAG retrieval/answer packaging.
- Reproduction documentation in
  `docs/reproduction/GRAPH_RAG_CONFLICT_ADJUDICATION_2026-06-10.md`.

Verified:

- `python -m unittest discover -s tests/unit -v` passed 19 tests.
- Conflict adjudication dry-run generated 59 payloads from 59 conflict records.
- Graph RAG index manifest captured 4554 abstracts, 18288 aligned triples,
  11155 fused edges, and 59 conflicts.
- Graph RAG answer dry-run for `SMN1` produced a bounded evidence package with
  32 supporting PMIDs, 8 abstracts, 24 aligned triples, 16 fused edges, and 8
  conflicts.

Not executed:

- Live LLM answer generation.
- Live LLM conflict adjudication.

Reason:

- Live runs require `SILICONFLOW_API_KEY` and would consume external LLM service
  quota. The implemented CLIs support live mode and keep outputs as dated
  artifacts without automatically mutating the canonical graph.
