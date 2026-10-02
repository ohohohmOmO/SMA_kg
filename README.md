# SMA Knowledge Graph

This repository builds a biomedical knowledge graph for Spinal Muscular Atrophy
(SMA). The current implementation collects SMA data from Open Targets and
PubMed, extracts relation triples from literature, fuses synonymous entities,
computes graph metrics, generates an HTML graph viewer, and evaluates extraction
quality.

## Current FYP repair delivery 2026-10-02

Read `docs/fyp/FYP_FOUR_REPAIRS_STATUS_2026-10-02.md` and
`docs/reproduction/FYP_FOUR_REPAIRS_2026-10-02.md` first. Canonical graph now
uses conservative typed identity:13,001 literature edges with all18,288 source
records. `docs/graph_viewer.html` is the full offline source explorer.
Current results/evidence UI: `artifacts/runs/fyp_four_repairs_final_2026-10-02/`.
Neo4j queries must scope `SMAGraphMetadata.name='active'` to version
`typed-v2-8a4dbccd4fdc22ca`;9,218 typed/source-scoped nodes,13,165 edges;
historical Entity graph retained. No automatic clear or semantic identity merge.
Main human strict support26.3%; screening has substantial coverage loss and does
not establish sufficient extraction quality. Report scope now matches the core;
GraphRAG/answer citation/claim validation remain future work. Historical pipeline
counts and older commands below describe their dated runs, not current acceptance.

## Start Here

- Agent and contributor rules: `AGENTS.md`
- Run checklist: `docs/agents/PLAN.md`
- Issue log: `docs/agents/ISSUE_LOG.md`
- Latest handoff: `docs/PROJECT_HANDOFF_2026-06-09.md`
- Current hardening notes: `docs/reproduction/ENGINEERING_HARDENING_2026-06-09.md`
- Stage 3 preparation status: `docs/reproduction/STAGE3_PREP_2026-06-09.md`
- Pre-improvement baseline: `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`
- Archived old overview: `docs/archive/SMA_KG_Project_Overview_OLD.md`

Use the latest handoff for project onboarding. Older handoff snapshots have
been removed so `docs/PROJECT_HANDOFF_2026-06-09.md` is the source of truth.

## Environment

Use the conda environment prepared for this repository:

```powershell
conda activate KG_SMA_env
python --version
python -m pip install -r requirements.txt
```

Store local secrets in `.env` or `.env.local` by copying `.env.example`. Real
secret files are ignored by git and must not be committed.

External services and environment variables:

- `SILICONFLOW_API_KEY` for LLM extraction and LLM-based evaluation.
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for Neo4j import and topology
  checks.
- `HF_ENDPOINT`, commonly `https://hf-mirror.com`, for HuggingFace model access.

## Repository Layout

```text
data/
  raw/            PubMed abstracts
  external/       Open Targets baseline data
  interim/        mapped and aligned intermediate triples
  processed/      extracted, fused, evaluated, and analyzed outputs
src/
  crawler/        Open Targets and PubMed acquisition
  extraction/     LLM extraction, rule candidates, verification, merge step
  fusion/         dictionary mapping, semantic alignment, triple aggregation
  database/       Neo4j import, NetworkX analytics, PyVis graph export
  evaluation/     baseline evaluation, human/LLM scoring, novelty analysis
resources/        Biomedical schema and entity dictionary resources
notebooks/        BERTopic exploration and topic visualization
docs/             handoff snapshots, generated graph viewer, agent docs
artifacts/        archived run reports and ad hoc test results
tests/smoke/      lightweight external API smoke tests
lib/              vendored browser libraries used by generated HTML
```

## Pipeline

Run from the repository root.

```powershell
python src/crawler/api_fetcher.py
python src/crawler/pubmed_crawler.py
python src/crawler/topic_clustering.py
python src/crawler/topic_balanced_pubmed.py --topic-terms-file <topic_terms.json>

python src/extraction/run_stage2_extraction.py --run-dir artifacts/runs/stage2_extraction_<stamp> --llm-limit -1 --chunk-size 5 --parallel-workers 32 --promote
python src/extraction/verify_rule_candidates.py --input-file data/interim/rule_candidate_triples.jsonl --limit 50
python src/extraction/build_gold_candidates.py --run-dir artifacts/runs/stage2_gold_candidates_<stamp> --limit 750

python src/fusion/run_stage3_fusion.py --run-dir artifacts/runs/stage3_fusion_<stamp> --promote

python src/database/run_stage4_graph.py --run-dir artifacts/runs/stage4_graph_database_<stamp>

python src/evaluation/baseline_eval_advanced.py
python src/evaluation/ablation_study.py
python src/evaluation/novelty_analysis.py
```

Optional steps that require external services:

```powershell
python src/database/neo4j_importer.py
python src/evaluation/topology_eval.py
python src/evaluation/metrics_calculator.py
```

## Current Outputs

- `data/raw/pubmed_sma_abstracts.jsonl`: PubMed SMA abstracts.
- `data/processed/clustered_abstracts.jsonl`: Stage 1 topic clustering output.
- `data/external/sma_gda_baseline.jsonl`: Open Targets gene-disease baseline.
- `data/processed/llm_extracted_triples.jsonl`: validated LLM extraction output.
- `data/processed/extracted_triples.jsonl`: Stage 2 canonical LLM-only output.
- `data/interim/rule_candidate_triples.jsonl`: local rule candidates for review,
  recall analysis, gold-standard sampling, and ablation.
- `data/interim/verified_rule_triples.jsonl`: optional LLM/human-verified rule
  candidates; not promoted automatically.
- `data/interim/mapped_triples.jsonl`: dictionary-normalized triples.
- `data/interim/aligned_triples.jsonl`: semantically aligned triples.
- `data/processed/fused_triples.jsonl`: fused unique graph edges.
- `data/interim/relation_conflicts.jsonl`: Stage 3 relation polarity conflicts
  requiring review.
- `data/interim/aggregation_rejected.jsonl`: Stage 3 rejected aggregation
  records.
- `data/processed/analytics_metrics.csv`: PageRank and community metrics.
- `docs/graph_viewer.html`: generated interactive graph viewer.
- `artifacts/reports/`: archived historical command outputs and evaluation
  reports.

As of 2026-06-09, Stage 1 acquisition/topic clustering, Stage 2 full LLM-only
extraction, Stage 3 fusion/alignment/conflict detection, and Stage 4 Neo4j plus
local graph generation have been rerun successfully. Current Stage 3/4 results
are recorded in `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`.

Open decisions before changing Stage 1 or Stage 2 inputs:

- `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`
- `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`

See `docs/PROJECT_HANDOFF_2026-06-09.md` for the current project handoff.

## FYP evaluation and evidence inspection — 2026-10-02

The completion protocol and current status are in
`docs/fyp/FYP_EVALUATION_PROTOCOL_2026-10-02.md` and
`docs/fyp/FYP_COMPLETION_STATUS_2026-10-02.md`. The completed offline experiment
package is now `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/`: open
`evidence_explorer.html` in a browser, read `summary_zh.md` and
`results_and_discussion.md`, and inspect the hash manifest and row-level outputs.

Reproduce into a NEW directory using `KG_SMA_env`:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/evaluation/run_fyp_evaluation.py --workbook 'outputs/fyp_gold_annotation_2026-10-01/SMA人工标注集_400条_最终全表复核版.xlsx' --run-dir 'artifacts/runs/fyp_evaluation_new_run' --label-provenance human_confirmed_all --provenance-note '用户在2026-10-02说明：这400条均为人工标记，最后给到ChatGPT完成表格的而已。'
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/evaluation/build_fyp_report.py --run-dir 'artifacts/runs/fyp_evaluation_new_run'
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/evaluation/build_fyp_graph_explorer.py --run-dir 'artifacts/runs/fyp_evaluation_new_run'
```

The runner never modifies the workbook, canonical data or Neo4j. The user
confirmed all 400 labels were assigned by humans and ChatGPT only assembled the
table. This statement is recorded in the latest run config and provenance; the
original workbook is unchanged. Use `--label-provenance human_confirmed_all`
with that actual `--provenance-note` to reproduce the confirmed attribution.
For a different unconfirmed source, retain `ai_assisted_unconfirmed`.
Fusion correctness
requires the separate 30-unit review; the browser exports these judgments as
JSON, validated by `src/evaluation/summarize_fusion_review.py`.

Source traceability, evidence adequacy, relation support and entity identity are
different measures. The evidence module is conservative lexical triage, not
semantic entailment. GraphRAG and claim-level validation remain future work.

Open `graph_explorer.html` for the complete frozen graph with bounded directed
neighbourhoods and full source joins. External associations retain their source
identifiers in a separate namespace. `USAGE_AND_ACCEPTANCE_zh.md` records actual
interface checks; these are agent-performed functional checks, not independent
user-study results or student activity logbooks.

Current readiness review: `docs/fyp/FYP_READINESS_REVIEW_2026-10-02.md`.
`audit_fyp_completion.py --run-dir <new-evaluation-run>` checks alignment
transformations and reproduces the typed-key overwrite; add `--attempt-live-db`
for read-only database checks. The current audit did not establish a live
connection. The core prototype is evaluated, but quality and draft-scope gates
remain open; no canonical graph was corrected or reimported by this audit.
