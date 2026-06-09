# SMA Knowledge Graph

This repository builds a biomedical knowledge graph for Spinal Muscular Atrophy
(SMA). The current implementation collects SMA data from Open Targets and
PubMed, extracts relation triples from literature, fuses synonymous entities,
computes graph metrics, generates an HTML graph viewer, and evaluates extraction
quality.

## Start Here

- Agent and contributor rules: `AGENTS.md`
- Run checklist: `docs/agents/PLAN.md`
- Issue log: `docs/agents/ISSUE_LOG.md`
- Current hardening notes: `docs/reproduction/ENGINEERING_HARDENING_2026-06-09.md`
- Stage 3 preparation status: `docs/reproduction/STAGE3_PREP_2026-06-09.md`
- Pre-improvement baseline: `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`
- Dated handoff snapshot: `docs/PROJECT_HANDOFF_2026-06-08.md`
- Archived old overview: `docs/archive/SMA_KG_Project_Overview_OLD.md`

The dated handoff is a snapshot of the repository state on 2026-06-08. It is
useful context, but it is not a mandatory preflight document for every task.

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

See `docs/PROJECT_HANDOFF_2026-06-08.md` for the detailed state and result
summary captured on 2026-06-08.
