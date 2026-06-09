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

### 2026-06-09 - Stage 4 analytics community IDs were non-deterministic

- Symptom: Two Stage 4 local reruns with identical `fused_triples.jsonl` and
  Open Targets inputs produced different `analytics_metrics.csv` and
  `graph_viewer.html` hashes. PageRank values were stable, but 516 of 607 nodes
  changed `Community_ID`.
- Cause: `graph_analytics.py` called
  `nx.community.louvain_communities()` without a fixed seed, then assigned
  community IDs from unordered community/node iteration.
- Fix: Added a fixed community seed, sorted communities and community members by
  node name, and sorted analytics output by `PageRank` then `Entity`.
- Verification: `artifacts/runs/stage4_graph_database_2026-06-09/` contains two
  fixed-seed reruns with identical hashes:
  `analytics_metrics_fixed_first.csv` and `analytics_metrics_fixed_second.csv`
  both hash to
  `3e3f8c1653a19cd5adcc303664b4a528b37e20dbf798f19a3a5cd668b9ce3116`;
  `graph_viewer_fixed_first.html` and `graph_viewer_fixed_second.html` both
  hash to
  `fe93189804ef2a982bb6c16147c8266e139fe3bc1a90407c6734284bd1d050d0`.

### 2026-06-09 - Stage 3 outputs were stale after stabilized Stage 2

- Symptom: Stage 3 fusion outputs still reflected the older 2664-triple Stage 2
  input, while the stabilized Stage 2 canonical input now contained 5738 merged
  triples.
- Cause: `dictionary_mapper.py`, `semantic_aligner.py`, and
  `triples_aggregator.py` write directly to canonical output paths and had not
  been rerun after the Stage 2 promotion.
- Fix: Reran the Stage 3 scripts, captured pre-run snapshots, logs, output
  snapshots, a manifest, and validation statistics under
  `artifacts/runs/stage3_fusion_2026-06-09/`.
- Verification: Stage 3 now reports 5738 mapped triples, 5738 aligned triples,
  and 554 fused unique edges. A Stage 4 dry-read of
  `data/processed/fused_triples.jsonl` loaded all 554 records with 0 missing core
  fields.

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
