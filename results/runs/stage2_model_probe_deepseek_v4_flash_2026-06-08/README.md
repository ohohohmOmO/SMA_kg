# Stage 2 Model Probe - DeepSeek V4 Flash - 2026-06-08

This run probes `deepseek-ai/DeepSeek-V4-Flash` for the Stage 2 LLM extraction
task using the existing local `SILICONFLOW_API_KEY` from `.env`.

## Command

```powershell
python src/extraction/llm_extractor.py `
  --input-file data/raw/pubmed_sma_abstracts.jsonl `
  --output-file artifacts/runs/stage2_model_probe_deepseek_v4_flash_2026-06-08/deepseek_v4_flash_first5.jsonl `
  --offset 0 `
  --limit 5 `
  --model deepseek-ai/DeepSeek-V4-Flash `
  --max-tokens 1024 `
  --min-triples 0
```

## Result

- Exit code: 0
- Input slice: first 5 PubMed abstracts
- Output triples: 21
- Invalid JSONL lines: 0
- Unique PMIDs covered by emitted triples: 5
- Malformed LLM responses reported by extractor: 0
- Failed records reported by extractor: 0

This validates DeepSeek V4 Flash as the preferred model for the Stage 2
chunk/resume/validate/promote plan.
