# SMA Graph RAG And Conflict Adjudication Implementation Plan

Status: Pending user confirmation
Created: 2026-06-09

## Execution Rule

Do not start implementation until the user confirms this plan. Implementation
must remain on a feature branch named under:

`feature/huawei-ai应用工程师-ai技术应用/<specific-feature>-<timestamp>`

## Plan Summary

Implement a shared evidence-context layer first, then build two capabilities on
top of it:

1. SMA Graph RAG intelligent QA.
2. LLM-assisted relation conflict adjudication.

The implementation should be CLI-first, testable without external services, and
able to use live LLM/Neo4j integrations only when local `.env` provides the
required credentials.

## Phase 0: Confirmation And Branch Hygiene

- Confirm v1 delivery mode: CLI-first or FastAPI-included.
- Confirm canonical graph mutation policy: v1 should not mutate canonical graph
  outputs.
- Create a fresh implementation branch after confirmation if the current branch
  should remain documentation-only.

Exit criteria:

- User explicitly confirms the plan and any selected options.

## Phase 1: Shared Evidence Context

Files to add:

- `src/evidence/__init__.py`
- `src/evidence/context_builder.py`
- `tests/unit/test_evidence_context.py`

Capabilities:

- Load abstracts from `data/raw/pubmed_sma_abstracts.jsonl`.
- Load aligned triples from `data/interim/aligned_triples.jsonl`.
- Load fused edges from `data/processed/fused_triples.jsonl`.
- Build entity-pair evidence context for conflict adjudication.
- Build question-oriented evidence context for Graph RAG.
- Enforce prompt context limits.

Verification:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

## Phase 2: Conflict Adjudication Dry Run

Files to add:

- `src/fusion/adjudicate_relation_conflicts.py`
- `tests/unit/test_conflict_adjudication.py`

Capabilities:

- Load the current 59 conflict records.
- Assemble supporting evidence from aligned triples and PubMed abstracts.
- Emit dry-run adjudication payloads without requiring `SILICONFLOW_API_KEY`.
- Validate decision class names and required fields.
- Write run artifacts under
  `artifacts/runs/conflict_adjudication_<timestamp>/`.

Verification:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/fusion/adjudicate_relation_conflicts.py --dry-run --run-dir artifacts/runs/conflict_adjudication_probe_<timestamp>
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

Exit criteria:

- Dry-run produces 59 payload records.
- Manifest and validation summary are written.
- Canonical `data/processed/fused_triples.jsonl` is unchanged.

## Phase 3: Optional Live LLM Conflict Adjudication

Extend:

- `src/fusion/adjudicate_relation_conflicts.py`

Capabilities:

- Load local `.env` using the existing Stage 2 pattern.
- Call SiliconFlow with `deepseek-ai/DeepSeek-V4-Flash`.
- Parse strict JSON adjudication output.
- Write accepted, rejected, and unresolved outputs separately.
- Redact or avoid secrets in logs.

Verification:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/fusion/adjudicate_relation_conflicts.py --limit 3 --run-dir artifacts/runs/conflict_adjudication_live_probe_<timestamp>
```

Exit criteria:

- Live probe handles at least 3 conflicts.
- Bad JSON or API failures are captured as rejected/unresolved records.

## Phase 4: Graph RAG Retrieval Core

Files to add:

- `src/qa/__init__.py`
- `src/qa/retriever.py`
- `src/qa/build_index.py`
- `tests/unit/test_graph_rag_retrieval.py`

Capabilities:

- Build or refresh a local retrieval index from abstracts, aligned triples, and
  fused edges.
- Support lexical/entity matching first.
- Add embedding retrieval with sentence-transformers if available.
- Write index manifest under `data/processed/graph_rag_index_manifest.json`.
- Return top-k evidence context for a question.

Verification:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/qa/build_index.py --run-dir artifacts/runs/graph_rag_index_probe_<timestamp>
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

Exit criteria:

- At least five fixed questions retrieve non-empty contexts.
- Retrieval works without live LLM and without Neo4j.

## Phase 5: Graph RAG Answer Generator

Files to add:

- `src/qa/answer.py`
- `src/qa/run_graph_rag.py`
- `tests/unit/test_graph_rag_answer_schema.py`

Capabilities:

- Generate evidence-only answers from retrieved context.
- Support `--dry-run` to print the retrieved context without LLM calls.
- Support live LLM answer generation when `SILICONFLOW_API_KEY` is set.
- Include PMIDs, supporting triples, graph paths if available, and limitations.

Verification:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/qa/run_graph_rag.py --question "How does Nusinersen affect motor function?" --dry-run
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

Exit criteria:

- Dry-run returns structured evidence context.
- Live mode, when enabled, returns an answer with PMID citations.
- The prompt forbids unsupported claims.

## Phase 6: Documentation And Demo

Files to update:

- `README.md`
- `docs/PROJECT_HANDOFF_2026-06-09.md` or a new handoff if implementation is
  substantial.
- `docs/reproduction/` with a dated feature reproduction note.

Demo assets:

- Five Graph RAG demo questions.
- One conflict adjudication dry-run output sample.
- One live-mode example if API credentials are available.

Verification:

- Run unit tests.
- Run dry-run demos.
- Check git diff for secrets before committing.

## Risks And Mitigations

- Risk: LLM answer hallucinates unsupported claims.
  - Mitigation: strict evidence-only prompt and answer schema with limitations.
- Risk: Neo4j is unavailable during demo.
  - Mitigation: Graph RAG retrieval must work from local JSONL files.
- Risk: vector index adds heavyweight dependencies.
  - Mitigation: start with lexical/entity retrieval and optional embeddings.
- Risk: conflict adjudication overwrites graph evidence too early.
  - Mitigation: v1 writes separate adjudication artifacts only.

## Confirmation Checklist

Please confirm:

- V1 delivery mode: CLI-first.
- Canonical graph mutation: no mutation in v1.
- LLM provider: SiliconFlow DeepSeek V4 Flash by default.
- Neo4j: optional enhancement, not required for dry-run demos.
- First implementation target after confirmation: Phase 1 and Phase 2 together.
