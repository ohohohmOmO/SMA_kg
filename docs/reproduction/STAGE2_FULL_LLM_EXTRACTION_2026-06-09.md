# Stage 2 Full LLM Extraction - 2026-06-09

This document records the first full-corpus Stage 2 LLM extraction after the
Stage 2 policy changed from a 200-abstract LLM window plus rule fallback to
LLM-only canonical extraction over all current PubMed abstracts.

## Decision

- Canonical Stage 2 output is LLM-only.
- All current PubMed abstracts are assigned to LLM extraction with
  `--llm-limit -1`.
- Local rules remain auxiliary `Rule_Candidate` producers only. Because this
  full run assigns all PMIDs to LLM extraction, the rule candidate PMID split is
  empty for the canonical run.
- Same SiliconFlow API key extraction was run with `--parallel-workers 32`.

## Command

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src\extraction\run_stage2_extraction.py --run-dir artifacts\runs\stage2_extraction_llm_all_32w_2026-06-09 --llm-limit -1 --chunk-size 5 --parallel-workers 32 --model deepseek-ai/DeepSeek-V4-Flash --max-tokens 2048 --promote
```

## Inputs

- PubMed input: `data/raw/pubmed_sma_abstracts.jsonl`
- Input abstracts: 4554
- Input source run:
  `artifacts/runs/stage1_data_acquisition_full_2026-06-09/`
- Input SHA-256:
  `5cfe801ab22312fa0cad317da994ff55ba96913df12a79c9464f472d2a622a48`

## Run Artifacts

- Run directory:
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/`
- Split file:
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/stage2_input_split.json`
- Validation summary:
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/validation_summary.json`
- Manifest:
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/manifest.csv`
- Logs:
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/logs/`
- Chunks:
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/chunks/`

## Results

| Output | Records | Unique PMIDs | Bad JSON | Invalid triples | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| `data/processed/llm_extracted_triples.jsonl` | 18347 | 3656 | 0 | 0 | `d8fa349581edde56066c629a022cf658236bee004d6e5cf174188edf5529b1c2` |
| `data/processed/extracted_triples.jsonl` | 18288 | 3656 | 0 | 0 | `0d23d5dd162744dd70228905e6367800658e5d0af0b7328df50a6e62bfde76cb` |
| `data/interim/rule_candidate_triples.jsonl` | 0 | 0 | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Additional run facts:

- LLM PMIDs assigned: 4554
- Effective LLM limit: 4554
- Rule candidate PMIDs assigned: 0
- Chunk size: 5
- Chunk count: 911
- Parallel workers: 32
- Model: `deepseek-ai/DeepSeek-V4-Flash`
- Canonical policy: LLM-only; rule candidates are not merged into
  `extracted_triples.jsonl`.
- Promotion: true

## Interpretation

The run succeeded as a full Stage 2 canonical extraction. Not every abstract
yielded a triple: 3656 of 4554 PMIDs appear in the validated LLM output. The
canonical file removes 59 duplicate stage signatures from the raw LLM output,
leaving 18288 unique LLM-derived triples for Stage 3.

Next pipeline step: rerun Stage 3 fusion against
`data/processed/extracted_triples.jsonl`.
