# Implementation Status - 2026-06-10

Feature scope:

- SMA Graph RAG intelligent question answering.
- Relation-conflict automatic adjudication.

Status: v1 implemented and locally verified.

Completed:

- Evidence Context builder over local PubMed abstracts, aligned triples, fused
  edges, and conflict records.
- Conflict adjudication CLI with dry-run payload generation and live LLM mode.
- Graph RAG retrieval CLI with lexical/entity retrieval, `hybrid_tfidf`
  reranking, optional read-only Neo4j neighborhood expansion, and bounded
  evidence contexts.
- Graph RAG answer CLI with dry-run evidence packages and live LLM mode.
- Manifest-only Graph RAG index over canonical JSONL inputs.
- Conflict adjudication review proposal CLI that converts live adjudications
  into human-approved promotion proposals without mutating the canonical graph.
- Unit tests for evidence context, conflict adjudication schema/dry-run, and
  Graph RAG retrieval/answer packaging.
- Reproduction documentation in
  `docs/reproduction/GRAPH_RAG_CONFLICT_ADJUDICATION_2026-06-10.md`.

Verified:

- `python -m unittest discover -s tests/unit -v` passed 22 tests.
- Conflict adjudication dry-run generated 59 payloads from 59 conflict records.
- Graph RAG index manifest captured 4554 abstracts, 18288 aligned triples,
  11155 fused edges, and 59 conflicts.
- Graph RAG answer dry-run for `SMN1` produced a bounded evidence package with
  32 supporting PMIDs, 8 abstracts, 24 aligned triples, 16 fused edges, and 8
  conflicts.
- Five planned Graph RAG demo questions produced bounded dry-run evidence
  packages.
- Live Graph RAG answer probe completed with 8 supporting PMIDs.
- Live conflict adjudication probe completed with 1 valid adjudication and 0
  failed records.
- `hybrid_tfidf` retrieval probe completed with local TF-IDF cosine reranking.
- Neo4j neighborhood probe completed with 67 read-only neighborhood records.
- Conflict adjudication review proposal generated 1 proposal requiring human
  approval.

Not executed:

- Full 59-conflict live adjudication.
- Automatic canonical graph promotion.

Reason:

- Full live adjudication would consume more external LLM service quota.
- Canonical graph promotion is intentionally gated by human review.
