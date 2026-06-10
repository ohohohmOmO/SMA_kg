# Graph RAG And Conflict Adjudication V1 - 2026-06-10

This run implements the user-approved plan for two AI-application features:

- SMA Graph RAG intelligent question answering.
- Relation-conflict automatic adjudication.

The architecture follows the agreed responsibility split:

- Local retrieval finds evidence from repository artifacts.
- The LLM, when enabled, only understands supplied evidence, generates answers,
  and adjudicates conflicts.

## Branch

```text
feature/huawei-ai应用工程师-ai技术应用/graph-rag-conflict-prd-plan-20260609-225214
```

## Implemented Files

- `src/evidence/loaders.py`
- `src/evidence/context_builder.py`
- `src/fusion/adjudicate_relation_conflicts.py`
- `src/qa/retriever.py`
- `src/qa/build_index.py`
- `src/qa/answer.py`
- `src/qa/run_graph_rag.py`
- `tests/unit/test_evidence_context.py`
- `tests/unit/test_conflict_adjudication.py`
- `tests/unit/test_graph_rag.py`

## Inputs

The dry-runs used the current canonical and interim graph artifacts:

| Input | Records | SHA-256 |
| --- | ---: | --- |
| `data/raw/pubmed_sma_abstracts.jsonl` | 4554 | `5cfe801ab22312fa0cad317da994ff55ba96913df12a79c9464f472d2a622a48` |
| `data/interim/aligned_triples.jsonl` | 18288 | `65fc3e961e37e5361b47dd46dccef4916575d0e3b71130a8e6c775a18b36e58e` |
| `data/processed/fused_triples.jsonl` | 11155 | `1771293aad8258befe717c7c7ca00c349fe5fdb782b84245b1357ad45e332b5a` |
| `data/interim/relation_conflicts.jsonl` | 59 | `96c8923c9d67776b00936169323ee092979870d40b15c5a932d37a022b2924db` |

## Commands

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v

& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/fusion/adjudicate_relation_conflicts.py --dry-run --run-dir artifacts/runs/conflict_adjudication_dry_run_2026-06-10_121608

& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/qa/build_index.py --run-dir artifacts/runs/graph_rag_index_2026-06-10_121608

& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/qa/run_graph_rag.py --question 'What evidence links SMN1 to spinal muscular atrophy?' --dry-run --output-file artifacts/runs/graph_rag_answer_probe_2026-06-10_121608/answer_dry_run.json
```

## Results

- Unit tests: 19 passed.
- Conflict adjudication dry-run:
  - Run directory:
    `artifacts/runs/conflict_adjudication_dry_run_2026-06-10_121608/`
  - Input conflicts: 59.
  - Payloads written: 59.
  - Canonical graph mutated: false.
- Graph RAG index:
  - Run directory: `artifacts/runs/graph_rag_index_2026-06-10_121608/`
  - Manifest written to `data/processed/graph_rag_index_manifest.json`.
  - Retrieval mode: `lexical_entity`.
- Graph RAG answer dry-run:
  - Run directory:
    `artifacts/runs/graph_rag_answer_probe_2026-06-10_121608/`
  - Status: `dry_run_requires_llm`.
  - Supporting PMIDs: 32.
  - Abstracts in Evidence Context: 8.
  - Aligned triples in Evidence Context: 24.
  - Fused edges in Evidence Context: 16.
  - Conflict records in Evidence Context: 8.

## Live LLM Boundary

Live conflict adjudication and live answer generation are implemented but were
not executed in this reproduction run. They require `SILICONFLOW_API_KEY` from
the ignored local environment and should write dated artifacts under
`artifacts/runs/`. V1 live runs do not mutate the canonical graph automatically.

## Acceptance Status

- Local retrieval can run independently and is responsible for finding
  evidence.
- LLM calls are optional and consume bounded Evidence Context payloads only.
- Conflict adjudication dry-run is reproducible without LLM or Neo4j.
- Graph RAG answer dry-run is reproducible without LLM or Neo4j.
- New artifacts are written under `artifacts/runs/`.
- Unit tests cover the new core logic.
