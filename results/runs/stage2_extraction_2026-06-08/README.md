# Stage 2 Extraction Run - 2026-06-08

This directory stores the reproducibility evidence for the 2026-06-08 rerun of
the second pipeline stage.

## Scope

Stage 2 covers:

- `src/extraction/llm_extractor.py`
- `src/extraction/local_pipeline.py`
- `src/extraction/merge_triples.py`

The LLM extractor was not rerun because no real `SILICONFLOW_API_KEY` was
available in the environment or local `.env` files. Running it without a key
would retry each of the first 200 abstracts and overwrite the historical LLM
output with failed or empty data.

The local regex fallback extractor and merge step were rerun successfully.

## Contents

- `llm_extractor_blocked.log`: reason the LLM extractor was not rerun
- `local_pipeline.log`: captured log for `src/extraction/local_pipeline.py`
- `merge_triples.log`: captured log for `src/extraction/merge_triples.py`
- `manifest.csv`: output paths, counts, field checks, duplicate counts, sizes,
  and SHA-256 hashes
- `field_summary.txt`: compact source/count summary
- `pre_run_outputs/`: snapshot of the previous stage-2 outputs before rerun
- `outputs/`: snapshot copies of the current stage-2 outputs after rerun

## Results

- Historical LLM triples retained: 674 records
- Rerun regex fallback triples: 5101 records
- Rerun merged extracted triples: 5775 records
- All three JSONL outputs have 0 invalid JSON lines.

See `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md` for the
full stage-2 diagnosis appended to the requested document.
