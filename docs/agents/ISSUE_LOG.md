# Issue Log

Read this file before diagnosing failures. When a problem is successfully
resolved, append a new entry with the date, symptom, cause, fix, and
verification.

## Entry template

```md
### YYYY-MM-DD - Short title

- Symptom:
- Cause:
- Fix:
- Verification:
```

## Resolved issues

### 2026-06-08 - Stage 1 rerun outputs were not auditable

- Symptom: First-stage crawler reruns wrote directly to `data/external/` and
  `data/raw/`, overwriting canonical data without a dated run directory,
  manifest, log capture, or output snapshot.
- Cause: The crawler scripts use hard-coded output paths and do not generate run
  metadata. Historical loose outputs made it hard to tell which artifacts came
  from which run.
- Fix: Reran the stage with logs captured under
  `artifacts/runs/stage1_data_acquisition_2026-06-08/`, copied the reproduced
  outputs into that dated run directory, generated `manifest.csv`, and documented
  the convention in `artifacts/README.md`.
- Verification: `manifest.csv` reports 164 valid Open Targets JSONL rows and
  4555 valid PubMed JSONL rows with 0 invalid JSON lines.

### 2026-06-06 - Consolidated conda environment

- Symptom: The repository had multiple candidate conda environments (`kg_sma`,
  `kg_env`, and `base`) with inconsistent dependency coverage.
- Cause: `kg_sma` and `kg_env` were not aligned with the packages required by
  `requirements.txt` and observed imports in `src/`.
- Fix: Removed `kg_sma` and `kg_env`, then cloned `base` into `KG_SMA_env`.
- Verification: `KG_SMA_env` reports Python 3.13.5 and successfully imports
  `requests`, `urllib3`, `pandas`, `Bio`, `bertopic`, `sklearn`, `jupyter`,
  `ipykernel`, `tqdm`, `tenacity`, `openai`, `neo4j`, `sentence_transformers`,
  `pyvis`, `networkx`, `thefuzz`, and `numpy`.
