# Project Plan

This file is the first checkpoint before running commands, tests, scripts, or
pipeline steps in this repository.

For a dated snapshot of the implementation state on 2026-06-08, see
`docs/PROJECT_HANDOFF_2026-06-08.md`. It is reference material, not a mandatory
preflight document.

## Current operating rules

- Use conda environment `KG_SMA_env`.
- Run Python commands from the repository root unless a script documents another
  working directory.
- Check `docs/agents/ISSUE_LOG.md` before diagnosing any failure.
- After a successful fix, append the symptom, cause, fix, and verification to
  `docs/agents/ISSUE_LOG.md`.

## Runtime requirements

- Python environment: `KG_SMA_env`
- Dependency source: `requirements.txt` plus observed runtime imports
- Required for LLM stages: `SILICONFLOW_API_KEY`
- Required for Neo4j stages: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Recommended for HuggingFace downloads: `HF_ENDPOINT=https://hf-mirror.com`
- Neo4j service must be reachable for database import and topology evaluation.

## Pipeline shape

1. Data acquisition from Open Targets and PubMed.
2. LLM/NLP extraction of biomedical triples.
3. Semantic fusion and entity alignment.
4. Neo4j import plus graph analytics.
5. Evaluation, ablation study, and novelty discovery.

## Before each run

- Confirm `conda activate KG_SMA_env`.
- Confirm any required external service or API key for the script being run.
- Confirm input/output paths under `data/` match the intended pipeline phase.
- Prefer focused script-level verification before running the full pipeline.
