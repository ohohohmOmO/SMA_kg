# Repository Instructions

This repository builds a knowledge graph for Spinal Muscular Atrophy (SMA). It
combines PubMed/Open Targets data acquisition, LLM-based relation extraction,
semantic fusion, Neo4j import, graph analytics, visualization, and evaluation.

`docs/PROJECT_HANDOFF_2026-06-08.md` is a dated snapshot of the repository state
as of 2026-06-08. Use it when historical context is useful; do not treat it as a
mandatory preflight document because the project will continue to evolve.

## Operating workflow

Before running commands, tests, scripts, or pipeline steps, read
`docs/agents/PLAN.md`.

When an error, failed run, broken dependency, data issue, or unexpected behavior
appears, read `docs/agents/ISSUE_LOG.md` before diagnosing. If the problem is
successfully resolved, append a concise entry to `docs/agents/ISSUE_LOG.md` with
the date, symptom, root cause, fix, and verification command or result.

When completing a task that changes files, stage and commit the changes before
the final response unless the user explicitly asks not to commit.

Use local markdown issue tracking for this repo. PRDs and implementation issues
live under `.scratch/`; see `docs/agents/issue-tracker.md`.

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
