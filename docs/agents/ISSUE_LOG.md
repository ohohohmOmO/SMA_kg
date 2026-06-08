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

### 2026-06-09 - Stage 2 full extraction needed recoverable execution

- Symptom: Stage 2 LLM extraction was too slow and fragile as one monolithic
  200-record run. Earlier attempts could be interrupted and either leave partial
  `.tmp` data or risk stale/historical LLM outputs being mixed with fresh Regex
  output.
- Cause: The original Stage 2 flow had no chunk manifest, no resumable runner,
  no validation gate, and no promote-only-after-validation step.
- Fix: Added `src/extraction/run_stage2_extraction.py` to generate a fixed
  Stage 2 split, run DeepSeek V4 Flash in 20-PMID chunks, resume valid chunks,
  validate LLM/Regex/merged JSONL outputs, write run artifacts, and promote only
  after validation passes.
- Verification: `python src/extraction/run_stage2_extraction.py --run-dir artifacts/runs/stage2_extraction_full_2026-06-08_2335 --llm-limit 200 --chunk-size 20 --model deepseek-ai/DeepSeek-V4-Flash --max-tokens 2048 --promote` completed successfully. Validation reports 638 LLM triples, 5101 Regex triples, and 5738 merged triples with 0 bad JSON lines and 0 invalid triples; a Stage 3 dictionary-mapper dry-read loaded all 5738 merged triples without code changes.

### 2026-06-08 - Stage 2 LLM extraction could not be faithfully rerun

- Symptom: The second-stage LLM extractor could not be safely rerun because
  `SILICONFLOW_API_KEY` was missing. The local regex extractor and merge step
  could run, but the merged output would combine historical LLM triples with
  newly reproduced regex triples.
- Cause: `llm_extractor.py` requires a live SiliconFlow key, hard-codes the
  first 200 abstracts and output path, and has no dry-run, fixture, small-sample,
  or alternate-output mode. Running it without a key would trigger repeated
  failures and risk overwriting the historical LLM output.
- Fix: Preserved pre-run stage-2 outputs under
  `artifacts/runs/stage2_extraction_2026-06-08/pre_run_outputs/`, reran only
  the reproducible local regex and merge steps, wrote logs and a manifest under
  `artifacts/runs/stage2_extraction_2026-06-08/`, and documented the partial
  reproduction boundary.
- Verification: `manifest.csv` reports 674 historical LLM triples, 5101 rerun
  regex triples, and 5775 merged triples, each with 0 invalid JSON lines.

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
