# SMA Graph RAG And Conflict Adjudication PRD

Status: Pending user confirmation
Created: 2026-06-09
Branch: `feature/huawei-ai应用工程师-ai技术应用/graph-rag-conflict-prd-plan-20260609-225214`

## Purpose

Build two interview-visible AI application features on top of the current SMA
knowledge graph:

1. SMA Graph RAG intelligent question answering.
2. LLM-assisted relation conflict adjudication.

The two features should share a common evidence-context layer so the project
demonstrates more than isolated scripts: it should show an integrated AI
application that combines LLMs, vector retrieval, knowledge graphs, biomedical
NLP evidence, and reproducible engineering.

## Current Project Baseline

The current repository state provides enough material for both features:

- Stage 1 canonical PubMed abstracts: `4554`.
- Stage 2 canonical LLM-only triples: `18288`.
- Stage 3 fused graph edges: `11155`.
- Stage 3 relation conflict records: `59`.
- Stage 4 Neo4j import succeeded with `6648` nodes and `11208` relationships.
- Key inputs:
  - `data/raw/pubmed_sma_abstracts.jsonl`
  - `data/interim/aligned_triples.jsonl`
  - `data/processed/fused_triples.jsonl`
  - `data/interim/relation_conflicts.jsonl`
  - `data/processed/analytics_metrics.csv`

## Target Users

- Interview/demo evaluator: wants to see a clear AI application built from the
  existing project.
- Biomedical knowledge graph developer: wants to inspect evidence, graph paths,
  and conflict decisions.
- Research analyst: wants PMID-cited answers about SMA genes, drugs,
  phenotypes, and mechanisms.

## Canonical Terms

- Evidence Context: the shared evidence bundle used by both Graph RAG answers
  and conflict adjudication.
- Graph RAG Answer: an answer grounded in retrieved abstracts, evidence triples,
  and fused graph context.
- Conflict Adjudication: a structured decision about a relation conflict without
  silently rewriting canonical graph outputs.

These terms are also recorded in `CONTEXT.md`.

## Feature A: SMA Graph RAG Intelligent QA

### Goal

Allow users to ask natural-language SMA questions and receive concise,
evidence-grounded answers with PMIDs, relevant triples, graph paths, and
confidence signals.

### Supported Question Types

- Entity summary: "What is known about SMN1 in SMA?"
- Treatment evidence: "How does Nusinersen affect motor function?"
- Mechanism query: "Which mechanisms connect SMN protein and motor neuron
  degeneration?"
- Comparison query: "What evidence compares Risdiplam and Nusinersen?"
- Conflict-aware query: "Are there contradictory findings for Onasemnogene
  Abeparvovec?"

### Core Capabilities

- Build a local retrievable corpus from PubMed abstracts, aligned triples, fused
  triples, and graph metrics.
- Retrieve evidence with hybrid ranking:
  - lexical/entity matching over entity names and relations,
  - embedding/vector similarity over abstracts and evidence text,
  - optional Neo4j graph neighborhood expansion when Neo4j is reachable.
- Construct an evidence context with:
  - question,
  - matched entities,
  - retrieved abstracts,
  - supporting evidence triples,
  - fused graph edges,
  - PMIDs,
  - confidence and review status.
- Generate an answer with an LLM using only the evidence context.
- Return structured output as JSON and readable text.
- Provide a no-API dry-run mode that returns retrieved evidence context without
  calling the LLM.

### Output Contract

Graph RAG should write or return:

```json
{
  "question": "string",
  "answer": "string",
  "matched_entities": ["string"],
  "supporting_pmids": ["PMID"],
  "supporting_triples": [],
  "graph_paths": [],
  "limitations": ["string"],
  "model": "string",
  "retrieval": {
    "mode": "hybrid",
    "top_k": 8
  }
}
```

### Acceptance Criteria

- At least five fixed demo questions produce non-empty evidence contexts.
- Every generated answer cites at least one PMID or explicitly says no evidence
  was retrieved.
- The LLM prompt forbids unsupported biomedical claims outside retrieved
  evidence.
- Dry-run mode works without `SILICONFLOW_API_KEY`.
- Unit tests cover evidence-context assembly and output schema.

## Feature B: LLM-Assisted Relation Conflict Adjudication

### Goal

Use source evidence to classify and explain the existing 59 relation conflicts,
without silently overwriting the canonical fused graph.

### Conflict Classes

- `supported_context_dependent`: both relation polarities are supported in
  different contexts.
- `extraction_error`: at least one relation is not supported by its evidence.
- `direction_error`: relation direction is wrong for at least one edge.
- `relation_normalization_issue`: the apparent conflict comes from relation
  alias or polarity mapping.
- `real_conflict_needs_human_review`: the conflict appears genuine but requires
  expert review.
- `insufficient_evidence`: available evidence is too weak or missing.

### Core Capabilities

- Load each conflict from `data/interim/relation_conflicts.jsonl`.
- Collect supporting raw aligned triples for the same entity pair from
  `data/interim/aligned_triples.jsonl`.
- Attach source abstracts from `data/raw/pubmed_sma_abstracts.jsonl`.
- Build an evidence context per conflict.
- Generate a deterministic adjudication payload in dry-run mode.
- Optionally call an LLM verifier to classify the conflict.
- Write accepted/rejected/unresolved decisions to a separate run artifact.
- Keep canonical `data/processed/fused_triples.jsonl` unchanged unless a later
  explicit promotion command is added and confirmed.

### Output Contract

Adjudication should write JSONL records shaped like:

```json
{
  "conflict_id": "SMA-CONFLICT-0001",
  "entity_1": {"name": "string", "type": "string"},
  "entity_2": {"name": "string", "type": "string"},
  "conflicting_relations": ["IMPROVES", "WORSENS"],
  "decision": "extraction_error",
  "retained_relations": ["IMPROVES"],
  "rejected_relations": ["WORSENS"],
  "confidence": 0.0,
  "rationale": "string",
  "supporting_pmids": ["PMID"],
  "model": "string",
  "review_status": "adjudicated"
}
```

### Acceptance Criteria

- Dry-run mode creates 59 adjudication payloads from the current conflict file.
- Missing abstracts or missing supporting triples are reported, not ignored.
- Live LLM mode writes accepted and rejected records separately.
- The output includes a validation summary and manifest under
  `artifacts/runs/conflict_adjudication_<timestamp>/`.
- Unit tests cover payload assembly, class validation, and missing evidence
  handling.

## Shared Evidence Context Requirements

Both features should use the same evidence-context builder rather than creating
two incompatible evidence formats.

Shared module target:

- `src/evidence/context_builder.py`

Shared responsibilities:

- Load PubMed abstracts by PMID.
- Load aligned triples by entity pair and relation.
- Load fused graph edges.
- Normalize entity-pair matching consistently with Stage 3 entity naming.
- Limit context size for LLM prompts.
- Preserve provenance fields such as PMID, evidence text, extraction engine, and
  confidence.

## Non-Goals

- Do not rerun Stage 1, Stage 2, Stage 3, or Stage 4.
- Do not promote topic-balanced PubMed candidates.
- Do not fine tune BioBERT/UIE-med in this feature.
- Do not mutate canonical fused graph outputs during the first implementation.
- Do not require Neo4j for dry-run Graph RAG; Neo4j graph expansion is optional
  when credentials and service are available.

## Runtime And Secret Requirements

- `SILICONFLOW_API_KEY`: required only for live LLM answer generation or live
  conflict adjudication.
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: optional for graph expansion and
  demos that query live Neo4j.
- `HF_ENDPOINT`: recommended for embedding model downloads.
- Real secret values must remain only in ignored `.env` or `.env.local`.

## Recommended Technical Direction

Use a conservative first version:

- Local JSONL/CSV loaders for canonical data.
- A local vector index backed by sentence-transformers embeddings and an
  on-disk artifact manifest.
- Neo4j expansion as optional integration, not a hard dependency.
- SiliconFlow DeepSeek V4 Flash as the default live LLM because it is already
  used in Stage 2.
- Deterministic dry-run paths for tests and interview demonstration.

## Decisions Needing User Confirmation

Recommended defaults:

- Build both features as a combined feature package because they share evidence
  context.
- Start with CLI-first implementation, then add API/UI only after the core
  evidence and adjudication logic works.
- Keep canonical graph files immutable in v1.
- Use local vector storage first; postpone a hosted vector database until needed.

Open question for confirmation:

Should v1 be CLI-first with JSON/Markdown outputs, or should it include a small
FastAPI service immediately?

Recommended answer: CLI-first. It is faster, easier to test, and better aligned
with the current repository's runner pattern.
