# KG SMA Project Handoff - 2026-06-09

## Purpose

This handoff lets a fresh agent or developer quickly understand the SMA knowledge graph repository at `D:\kg_sma_0420` and continue work without relying on chat memory.

The project builds a biomedical knowledge graph for Spinal Muscular Atrophy (SMA). It collects Open Targets and PubMed data, clusters literature topics, extracts biomedical triples with an LLM, validates and scores those triples, fuses entities/relations, detects relation conflicts, imports the graph into Neo4j, computes graph analytics, and generates an HTML graph viewer.

## Current Status

The 2026-06-09 Stage 1-4 engineering hardening work is complete and committed.

Latest completed-state commit before this project-local handoff was added:
`b228f64 Archive completed hardening plan`.

Important current facts:

- Stage 1 acquisition rerun succeeded: 4554 PubMed abstracts and 164 Open Targets records.
- Stage 1 topic clustering rerun succeeded: 4554 clustered abstracts and 67 topics.
- Stage 2 canonical extraction is LLM-only over all 4554 PubMed abstracts, using `deepseek-ai/DeepSeek-V4-Flash` with 32 workers.
- Stage 2 canonical output has 18288 validated LLM-derived triples.
- Stage 3 fusion/alignment rerun succeeded using `NeuML/pubmedbert-base-embeddings`.
- Stage 3 canonical fused output has 11155 fused edges and 59 relation conflict records.
- Stage 4 Neo4j import and local graph generation succeeded: 6648 Neo4j nodes, 11208 relationships, 0 isolated nodes.
- Current working tree was clean after commit `b228f64` when this handoff was generated.

## Start Here In The Repo

Read these first:

- `AGENTS.md`: operating rules, secrets policy, conda environment, commit policy.
- `docs/agents/PLAN.md`: current status, runtime checklist, open decisions.
- `README.md`: repository layout, pipeline commands, current outputs.
- `docs/agents/ISSUE_LOG.md`: resolved failures and fixes.
- `docs/reproduction/ENGINEERING_HARDENING_2026-06-09.md`: implementation summary for the hardening work.
- `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`: full Stage 2 LLM extraction report.
- `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`: full Stage 3/4 rerun report.

Historical reference only:

- `docs/PROJECT_HANDOFF_2026-06-08.md`
- `docs/agents/archive/PLAN_COMPLETED_2026-06-09.md`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`

## Environment

Use the conda environment `KG_SMA_env`.

Direct Python path for non-interactive commands:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' --version
```

Secrets must stay in the ignored local `.env` or `.env.local` file. Do not write real API keys, tokens, or Neo4j passwords into source code, docs, logs, manifests, generated examples, or committed artifacts.

Required runtime variables:

- `SILICONFLOW_API_KEY` for LLM extraction/evaluation.
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for Neo4j import/topology.
- `HF_ENDPOINT`, usually `https://hf-mirror.com`, for HuggingFace model access.

## Repository Shape

Main directories:

- `src/crawler/`: Open Targets/PubMed acquisition and topic clustering/retrieval.
- `src/extraction/`: LLM extraction, rule candidates, rule verification, Stage 2 runner, gold candidate builder.
- `src/biomedical/`: shared schema normalization and confidence scoring.
- `src/fusion/`: dictionary mapping, semantic alignment, aggregation, conflict detection, Stage 3 runner.
- `src/database/`: Neo4j importer, Stage 4 runner, NetworkX analytics, PyVis graph viewer.
- `src/evaluation/`: topology evaluation, metrics, ablation, novelty analysis.
- `resources/`: biomedical schema and entity dictionary resources.
- `data/`: current canonical and intermediate outputs.
- `artifacts/runs/`: dated run artifacts, logs, manifests, validation summaries, and output snapshots.
- `docs/reproduction/`: reproduction and hardening reports.
- `.scratch/`: local markdown issue tracker.

## Current Canonical Outputs

Stage 1:

- `data/raw/pubmed_sma_abstracts.jsonl`
- `data/external/sma_gda_baseline.jsonl`
- `data/processed/clustered_abstracts.jsonl`

Stage 2:

- `data/processed/llm_extracted_triples.jsonl`
- `data/processed/extracted_triples.jsonl`
- `data/interim/rule_candidate_triples.jsonl`

Stage 3:

- `data/interim/mapped_triples.jsonl`
- `data/interim/aligned_triples.jsonl`
- `data/processed/fused_triples.jsonl`
- `data/interim/relation_conflicts.jsonl`
- `data/interim/aggregation_rejected.jsonl`

Stage 4:

- `data/processed/analytics_metrics.csv`
- `docs/graph_viewer.html`

## Current Run Artifacts

Most important completed run directories:

- `artifacts/runs/stage1_data_acquisition_full_2026-06-09/`
- `artifacts/runs/stage1_topic_clustering_full_2026-06-09/`
- `artifacts/runs/stage1_topic_balanced_pubmed_full_2026-06-09/`
- `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/`
- `artifacts/runs/stage3_fusion_full_2026-06-09/`
- `artifacts/runs/stage4_graph_full_2026-06-09/`

Canonical outputs and run artifact snapshots may intentionally contain identical bytes. This is expected after promotion: canonical paths are the current working outputs, while `artifacts/runs/.../outputs/` are reproducibility snapshots tied to manifests and logs. Do not delete those duplicates unless the user explicitly starts an artifact retention cleanup.

## Pipeline Commands

Use the repo root as working directory.

Stage 1:

```powershell
python src/crawler/api_fetcher.py
python src/crawler/pubmed_crawler.py
python src/crawler/topic_clustering.py
python src/crawler/topic_balanced_pubmed.py --topic-terms-file <topic_terms.json>
```

Stage 2 canonical full run:

```powershell
python src/extraction/run_stage2_extraction.py --run-dir artifacts/runs/stage2_extraction_<stamp> --llm-limit -1 --chunk-size 5 --parallel-workers 32 --promote
```

Stage 3 canonical full run:

```powershell
python src/fusion/run_stage3_fusion.py --run-dir artifacts/runs/stage3_fusion_<stamp> --alignment-model NeuML/pubmedbert-base-embeddings --promote
```

Stage 4 canonical full run:

```powershell
python src/database/run_stage4_graph.py --run-dir artifacts/runs/stage4_graph_<stamp> --input-file data/processed/fused_triples.jsonl --opentargets-file data/external/sma_gda_baseline.jsonl --promote
```

Verification:

```powershell
python -m py_compile src/fusion/run_stage3_fusion.py src/database/run_stage4_graph.py src/database/neo4j_importer.py src/evaluation/topology_eval.py tests/unit/test_biomedical_quality.py
python -m unittest discover -s tests/unit -v
```

## Open Decisions

These are tracked as local markdown issues and remain unresolved:

- `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`: decide whether to review and promote 27 topic-balanced PubMed candidate records.
- `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`: build a 500-1000 item reviewed gold-standard set before deciding whether BioBERT/UIE-med fine tuning is justified.
- Stage 3 conflict adjudication: `data/interim/relation_conflicts.jsonl` contains 59 conflict records. They are marked `needs_review`; no human/LLM adjudication has been done yet.

## Suggested Skills

- `diagnose`: use for failing scripts, validation mismatches, dependency issues, or unexpected graph/database behavior.
- `grill-with-docs`: use before changing project direction, schema semantics, extraction policy, evaluation strategy, or artifact retention policy.
- `handoff`: use again before ending a long session or after major new stages are completed.
- `to-issues`: use if the open decisions should be split into implementation tickets.
- `improve-codebase-architecture`: use if refactoring Stage 5/6 evaluation or artifact retention policy.

## Cautions

- Always read `docs/agents/PLAN.md` before running commands.
- Read `docs/agents/ISSUE_LOG.md` before diagnosing failures.
- Do not commit `.env`, `.env.local`, real API keys, or Neo4j passwords.
- Do not assume old files under `artifacts/runs/` are current canonical outputs; use `data/` and `docs/graph_viewer.html` for current promoted outputs.
- Do not merge rule candidates into Stage 2 canonical output unless they have explicit LLM or human verification.
- Do not promote topic-balanced PubMed candidates into Stage 1 canonical input without a review decision.
- After changing files, stage and commit before final response unless the user explicitly asks not to.
