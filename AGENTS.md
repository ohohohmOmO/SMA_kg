# Repository Instructions

This repository builds a knowledge graph for Spinal Muscular Atrophy (SMA). It
combines PubMed/Open Targets data acquisition, LLM-based relation extraction,
semantic fusion, Neo4j import, graph analytics, visualization, and evaluation.

`docs/PROJECT_HANDOFF_2026-06-09.md` is the current project handoff. Use it for
quick onboarding when the current development state is unclear.

## Operating workflow

Before running commands, tests, scripts, or pipeline steps, read
`docs/agents/PLAN.md`.

If context was compacted, memory was lost, or the current development state is
uncertain, reread `AGENTS.md`, `docs/agents/PLAN.md`,
`docs/agents/ISSUE_LOG.md`, `CONTEXT.md`, and the current stage's reproduction
or run artifact documents before continuing. Do not rely on remembered paths,
counts, hashes, environment state, or pipeline status when uncertainty is
present.

When an error, failed run, broken dependency, data issue, or unexpected behavior
appears, read `docs/agents/ISSUE_LOG.md` before diagnosing. If the problem is
successfully resolved, append a concise entry to `docs/agents/ISSUE_LOG.md` with
the date, symptom, root cause, fix, and verification command or result.

When completing a task that changes files, stage and commit the changes before
the final response unless the user explicitly asks not to commit.

Use local markdown issue tracking for this repo. PRDs and implementation issues
live under `.scratch/`; see `docs/agents/issue-tracker.md`.

## Secrets and API keys

Never hardcode API keys, database passwords, tokens, or other secrets in source
code, notebooks, committed docs, tests, or generated examples.

Store real local secrets in `.env` or `.env.local` at the repository root. These
files are ignored by git and must stay uncommitted. Commit only sanitized
templates such as `.env.example`.

Keep the real `SILICONFLOW_API_KEY` and Neo4j credentials
(`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`) together in the same ignored local
`.env` file for this repository. Do not split real secret values into committed
docs, scripts, notebooks, or generated artifacts.

When code needs a secret, read it from environment variables, for example
`SILICONFLOW_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, or
`HF_ENDPOINT`. If a task requires a new secret, add a placeholder to
`.env.example` and document the variable name, but do not write the real value.

## Conda environment

Use the `KG_SMA_env` conda environment for all future work in this repository.

Verified environment:

- Conda env: `KG_SMA_env`
- Env path: `C:\Users\jon15\anaconda3\envs\KG_SMA_env`
- Python: `3.13.5`
- Created by cloning `base`

Activation:

```powershell
conda activate KG_SMA_env
```

Direct Python path for non-interactive commands:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' --version
```

If dependencies need refreshing, run:

```powershell
python -m pip install -r requirements.txt
```

Project dependencies come from both `requirements.txt` and observed runtime
imports in `src/` and `notebooks/`. Verified key packages include:

- `requests`, `urllib3`, `pandas`, `biopython`
- `bertopic`, `scikit-learn`, `sentence-transformers`, `numpy`
- `jupyter`, `ipykernel`, `tqdm`, `tenacity`
- `openai`, `neo4j`, `pyvis`, `networkx`, `thefuzz`, `spacy`

External runtime requirements:

- `SILICONFLOW_API_KEY` for LLM extraction and LLM-based evaluation
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for Neo4j import/topology steps
- `HF_ENDPOINT`, usually `https://hf-mirror.com`, for HuggingFace model access
- A reachable Neo4j instance when running database import or topology scripts

## Agent skills

### Issue tracker

Issues and PRDs are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage labels use the default mattpocock/skills vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository: read root `CONTEXT.md` if present, then relevant ADRs under `docs/adr/`. See `docs/agents/domain.md`.
