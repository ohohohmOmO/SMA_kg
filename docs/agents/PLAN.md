# Project Plan

This file is the first checkpoint before running commands, tests, scripts, or
pipeline steps in this repository.

The 2026-06-09 engineering hardening plan has been completed and archived at:

- `docs/agents/archive/PLAN_COMPLETED_2026-06-09.md`

## Current Operating Rules

- Use conda environment `KG_SMA_env`.
- Run Python commands from the repository root unless a script documents another
  working directory.
- Check `docs/agents/ISSUE_LOG.md` before diagnosing any failure.
- After a successful fix, append the symptom, cause, fix, and verification to
  `docs/agents/ISSUE_LOG.md`.
- When context is compacted, memory is uncertain, or the current development
  state is unclear, reread the reference documents listed below before acting.
- When completing a task that changes files, stage and commit the changes before
  the final response unless the user explicitly asks not to commit.

## Runtime Requirements

- Python environment: `KG_SMA_env`
- Dependency source: `requirements.txt` plus observed runtime imports
- Required for LLM stages: `SILICONFLOW_API_KEY`
- Required for Neo4j stages: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Recommended for HuggingFace downloads: `HF_ENDPOINT=https://hf-mirror.com`
- Neo4j service must be reachable for database import and topology evaluation.

Real secrets must stay in the ignored local `.env` file. Do not write real API
keys or passwords to source code, committed docs, test fixtures, logs,
manifests, or generated examples.

## Historical Development Status - 2026-06-09

The Stage 1-4 hardening work requested on 2026-06-09 is complete.

- Stage 1 acquisition hardening is complete and rerun successfully.
- Stage 1 topic clustering hardening is complete and rerun successfully.
- Stage 1 topic-balanced retrieval is implemented and rerun, but its 27
  candidate records are not promoted into canonical PubMed input. The decision
  is tracked in
  `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`.
- Stage 2 LLM-only hardening is complete and rerun successfully over all 4554
  canonical PubMed abstracts with 32 workers.
- Stage 2 canonical output is `data/processed/extracted_triples.jsonl`, with
  18288 validated LLM-derived triples and SHA-256
  `0d23d5dd162744dd70228905e6367800658e5d0af0b7328df50a6e62bfde76cb`.
- BioBERT/UIE-med fine tuning is not started. The gold-standard review decision
  is tracked in
  `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`.
- Stage 3 full rerun is complete and promoted. Current Stage 3 output is
  `data/processed/fused_triples.jsonl`, with 11155 fused edges and SHA-256
  `1771293aad8258befe717c7c7ca00c349fe5fdb782b84245b1357ad45e332b5a`.
  Conflict detection wrote 59 conflict records to
  `data/interim/relation_conflicts.jsonl`.
- Stage 4 full rerun is complete and promoted. Neo4j import succeeded with
  11155 fused literature triples and 164 Open Targets relationships. Topology
  evaluation reported 6648 nodes, 11208 relationships, average degree
  3.371841155234657, and 0 isolated nodes.

## Primary Reference Documents

Read these when starting, resuming after compaction, or resolving uncertainty:

- `AGENTS.md`
- `README.md`
- `docs/agents/PLAN.md`
- `docs/agents/ISSUE_LOG.md`
- `CONTEXT.md`
- `docs/PROJECT_HANDOFF_2026-06-09.md`
- `docs/reproduction/ENGINEERING_HARDENING_2026-06-09.md`
- `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`
- `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`

Historical or archived context:

- `docs/agents/archive/PLAN_COMPLETED_2026-06-09.md`

## Pipeline Shape

1. Data acquisition from Open Targets and PubMed.
2. Topic clustering and topic-balanced PubMed expansion.
3. LLM/NLP extraction of biomedical triples.
4. Semantic fusion, entity alignment, relation alignment, and conflict
   detection.
5. Neo4j import plus graph analytics and visualization.
6. Evaluation, ablation study, and novelty discovery.

## Output Naming And Promotion Rules

- Canonical outputs stay under `data/` and `docs/graph_viewer.html` only after
  validation passes.
- Every rerun writes dated artifacts under `artifacts/runs/<stage>_<date-or-stamp>/`.
- Every run directory should contain at least `manifest.csv`,
  `validation_summary.json` or equivalent, logs, and output snapshots.
- Canonical outputs and run artifact snapshots may intentionally contain the
  same bytes after promotion. Keep both unless the user explicitly starts an
  artifact-retention cleanup.
- New experimental outputs must be named by stage and purpose, for example
  `topic_balanced_pubmed_sma_abstracts.jsonl`, not loose ad hoc filenames.
- Promotion from run artifacts to canonical paths must be explicit and must only
  happen after schema and count validation.

## Open Decisions

- Review whether to promote the 27 topic-balanced PubMed candidate records:
  `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`
- Build and review a 500-1000 item gold-standard set before deciding whether
  BioBERT/UIE-med fine tuning is justified:
  `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`
- Review the 59 Stage 3 relation conflict records in
  `data/interim/relation_conflicts.jsonl` if the graph needs conflict
  adjudication rather than `needs_review` marking.

## Current FYP Repairs - 2026-10-02

Four requested repairs have implementation and acceptance evidence. Current status
is `docs/fyp/FYP_FOUR_REPAIRS_STATUS_2026-10-02.md`; commands and boundaries are
`docs/reproduction/FYP_FOUR_REPAIRS_2026-10-02.md`.

- Canonical raw: 18,288 unchanged LLM predictions; supplied400 labels human-assigned,
  ChatGPT formatted only, workbook untouched. No independent second review.
- Canonical fusion: 13,001 literature edges, 9,053 typed nodes, 36 potential
  conflict pairs, two self-loops; fused SHA-256
  `ecdd5e68a308309f423b5ade455d14131152f67dcf978579c9f254c9d7de0e5d`.
  All982 SMN2→SMN1 erroneous endpoints/618 PMIDs restored. Typed orthographic
  identity only; semantic proposals require review. Prior canonical backed up.
- Final evaluation: `artifacts/runs/fyp_four_repairs_final_2026-10-02/`.
  Same-input raw/dictionary/repaired edges13,697/13,080/13,001. 30-unit new
  mapping queue remains optional and unjudged; no mapping correctness rate.
- Context/type/label-blind model experiment preserved in
  `assertion_quality_repair_2026-10-02`; documented decimal-boundary correction
  in `assertion_quality_context_fixed_2026-10-02` replays same400 responses,
  no additional calls. Full sidecar keeps16,724 needs_review/1,564 candidates.
  Main strict26.3%; combined internal test46.7% among30/202 retained, only14/55
  strict positives. Intervals overlap; rules alone worsen strict precision.
  No adequate extraction quality, significant gain, recall/F1 or clinical claim.
- Active Neo4j version `typed-v2-8a4dbccd4fdc22ca`: 9,218 nodes and13,165
  source-specific edges; every property/provenance reconciled, legacy6,648/
  11,208 retained. Never clear the graph. Defaultqueries scope active version.
- Current `docs/graph_viewer.html` is full offline source explorer; typed
  MultiDiGraph analytics promoted with backups. Old PyVis/history retained.
- Five external FYP drafts revised, backed up and checked page-by-page. Scope:
  extraction support, typed fusion, evidence/assertion screening and source
  inspection. GraphRAG/answer citation/atomic claim validation future work.
  Final university dissertation, true learning/logbooks and signatures remain.
- 56 focused unit tests and actual browser checks pass. Full reconciliation is
  engineering acceptance; all biomedical mappings/assertions remain unadjudicated.

## Before Each Run

- Confirm `conda activate KG_SMA_env` or use
  `C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe` directly.
- Confirm any required external service or API key for the script being run.
- Confirm input/output paths under `data/` match the intended pipeline phase.
- Prefer focused script-level verification before running the full pipeline.
- If a script writes canonical output, ensure there is a dated run artifact and a
  validation gate before promotion.
