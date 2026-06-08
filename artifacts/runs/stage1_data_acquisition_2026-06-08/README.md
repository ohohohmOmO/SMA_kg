# Stage 1 Data Acquisition Run - 2026-06-08

This directory stores the reproducibility evidence for the 2026-06-08 rerun of
the first pipeline stage.

## Contents

- `opentargets_api_fetcher.log`: captured log for `src/crawler/api_fetcher.py`
- `pubmed_crawler.log`: captured log for `src/crawler/pubmed_crawler.py`
- `manifest.csv`: output paths, line counts, JSON validity counts, byte sizes,
  and SHA-256 hashes
- `outputs/`: snapshot copies of the data files produced by this rerun

The canonical pipeline outputs remain under `data/external/` and `data/raw/`.
The files under `outputs/` are retained as dated run artifacts.

## Commands

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' 'src\crawler\api_fetcher.py'
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' 'src\crawler\pubmed_crawler.py'
```

## Results

- `data/external/sma_gda_baseline.jsonl`: 164 lines, 0 invalid JSON lines
- `data/raw/pubmed_sma_abstracts.jsonl`: 4555 lines, 0 invalid JSON lines

See `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md` for the
full diagnosis and recommendations.
