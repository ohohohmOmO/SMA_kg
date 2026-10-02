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

## Current Development Status - 2026-06-09

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

## FYP Completion Work - 2026-10-02

- The proposed schedule is in `docs/fyp/FYP_COMPLETION_PLAN_2026-10-02.md`.
- Review instructions and verification boundaries are in
  `docs/fyp/HUMAN_REVIEW_AND_VALIDATION_GUIDE_2026-10-02.md`.
- `src/evaluation/audit_fyp_inputs.py` performs offline, read-only input and
  provenance checks, writing to a new dated run directory. The completed run
  is `artifacts/runs/fyp_readiness_audit_2026-10-02/`; it found no issues in
  the implemented structural/provenance checks. It does not establish
  biomedical correctness or semantic evidence support.
- The evidence-location diagnostic found 15733 exact matches, 136
  case/whitespace matches, and 2419 non-located evidence texts. It also
  generated alignment-change and conflict-evidence review queues.
- The original blank workbook remains pending. The user subsequently supplied
  `outputs/fyp_gold_annotation_2026-10-01/SMA人工标注集_400条_最终全表复核版.xlsx`
  with 400 integrated support/span labels. Its source reviewer metadata is
  `ChatGPT-GPT-5.6-Sol`. The user clarified on 2026-10-02 that all 400 labels
  were assigned by humans and ChatGPT only assembled the workbook. Record this
  attestation separately; original metadata stays unchanged. The source question
  is closed. Independent second-review fields are empty and agreement is absent.
- The compact-label adapter and offline evaluation are implemented in
  `src/evaluation/fyp_dataset.py` and `run_fyp_evaluation.py`. Original labels,
  identities and source fields are preserved; blank component fields are not
  imputed. Keep the older detailed-workbook reporter for its original protocol.
- Completed automated run: `artifacts/runs/fyp_evaluation_2026-10-02/`.
  Controlled raw/dictionary/semantic aggregation has 13697/13080/11155 unique
  relation edges, preserves all 18288 evidence records and reproduces canonical
  semantic aggregation byte-for-byte. Mapping correctness awaits a separate
  fixed 30-unit review, not the extraction workbook.
- Latest human-confirmed run:
  `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/`.
  The attestation is in its run config/review provenance. Numerical results
  and the fixed mapping queue are unchanged; earlier run artifacts remain
  historical snapshots and may still display the former unconfirmed status.
- `src/biomedical/evidence_validation.py` implements source-offset location,
  typography normalization, ordered fragments and conservative lexical triage.
  It leaves 1152 spans unlocated, offers fuzzy suggestions for review only,
  and does not establish semantic entailment. Internal PMID-disjoint test
  results are against the supplied reference labels, with provenance limits.
- Generated deliverables: offline `evidence_explorer.html`, scientific figures,
  `results_and_discussion.md`, `summary_zh.md`, JSON/CSV diagnostics and manifests
  inside the run. Reporting checkpoints are in
  `docs/fyp/FYP_EVALUATION_PROTOCOL_2026-10-02.md` and
  `docs/fyp/FYP_COMPLETION_STATUS_2026-10-02.md`.
- `build_fyp_graph_explorer.py` also builds `graph_explorer.html`: complete
  literature-edge/original-record/abstract joins, bounded directed neighbours,
  filters, potential conflicts and separately identified Open Targets records.
  Ten real browser functional checks are recorded in
  `USAGE_AND_ACCEPTANCE_zh.md`; these are not independent human user testing.
- Next human-dependent work: enter the 30 mapping judgments for a frozen
  mapping condition using the offline explorer. Independent agreement stays
  unavailable until independent reviewers provide labels. GraphRAG and
  semantic claim-validation modules remain incomplete and outside this run.
- Completion audit found incompatible SMN2→SMN1 and subtype transformations,
  reproduced a name-only alignment-map cross-type overwrite, and recorded the
  name-only Neo4j identity limitation. A current read-only DB connection was
  attempted but not established (`ServiceUnavailable`); no graph was modified.
  See `docs/fyp/FYP_READINESS_REVIEW_2026-10-02.md` and
  `.scratch/fyp-evaluation/issues/04-prevent-incompatible-alignment.md`.
  Core prototype/evaluation is delivered; final quality and draft-scope gates
  remain open. The preliminary DOCX still promises the three unbuilt modules.

## Before Each Run

- Confirm `conda activate KG_SMA_env` or use
  `C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe` directly.
- Confirm any required external service or API key for the script being run.
- Confirm input/output paths under `data/` match the intended pipeline phase.
- Prefer focused script-level verification before running the full pipeline.
- If a script writes canonical output, ensure there is a dated run artifact and a
  validation gate before promotion.
