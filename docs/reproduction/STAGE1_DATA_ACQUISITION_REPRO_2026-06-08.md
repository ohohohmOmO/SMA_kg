# Stage 1 Data Acquisition Reproduction - 2026-06-08

本文档记录第一阶段数据采集的复现结果与诊断结论。第一阶段在当前仓库中指：

- Open Targets SMA gene-disease association baseline: `src/crawler/api_fetcher.py`
- PubMed SMA literature abstract crawl: `src/crawler/pubmed_crawler.py`

本次复现没有参考旧 overview；判断来自实际源码、实际运行日志、当前产物统计和字段检查。

## Run Context

- 日期：2026-06-08
- 仓库：`D:\kg_sma_0420`
- Conda 环境：`KG_SMA_env`
- Python：`C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe`
- 运行前已阅读：`docs/agents/PLAN.md`
- 诊断前已阅读：`docs/agents/ISSUE_LOG.md`

## Output Convention

第一阶段的数据本体继续放在流水线约定目录：

- `data/external/sma_gda_baseline.jsonl`
- `data/raw/pubmed_sma_abstracts.jsonl`

本次复现的运行证据放在 dated run 目录：

- `artifacts/runs/stage1_data_acquisition_2026-06-08/`
- `artifacts/runs/stage1_data_acquisition_2026-06-08/manifest.csv`
- `artifacts/runs/stage1_data_acquisition_2026-06-08/opentargets_api_fetcher.log`
- `artifacts/runs/stage1_data_acquisition_2026-06-08/pubmed_crawler.log`
- `artifacts/runs/stage1_data_acquisition_2026-06-08/outputs/data/external/sma_gda_baseline.jsonl`
- `artifacts/runs/stage1_data_acquisition_2026-06-08/outputs/data/raw/pubmed_sma_abstracts.jsonl`

这样处理后，`data/` 仍是下游代码读取的规范位置，`artifacts/runs/` 则保存某次复现的日志、manifest 和快照，避免历史上 loose output 或 ad hoc output 难以追踪的问题。

## Commands Run

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' 'src\crawler\api_fetcher.py'
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' 'src\crawler\pubmed_crawler.py'
```

日志分别捕获到：

- `artifacts/runs/stage1_data_acquisition_2026-06-08/opentargets_api_fetcher.log`
- `artifacts/runs/stage1_data_acquisition_2026-06-08/pubmed_crawler.log`

## Reproduction Results

| Product | Old observed count | Reproduced count | JSON validity | SHA-256 |
| --- | ---: | ---: | --- | --- |
| `data/external/sma_gda_baseline.jsonl` | 161 | 164 | 0 bad JSON lines | `f02cb91fb0e6e75debcd549b615aadb6d7a50965cd9ea3bff3eebb13444b76cb` |
| `data/raw/pubmed_sma_abstracts.jsonl` | 1840 | 4555 | 0 bad JSON lines | `21015fe3963a1ed038e3aa5e43fc719cb3bd823e9903630aaa78d5d336e91aaa` |

Additional checks:

- Open Targets records: 164
- Open Targets unique genes: 164
- Open Targets missing `gene_symbol`: 0
- Open Targets missing `target_id`: 0
- Open Targets missing `score`: 0
- Open Targets disease ID: `MONDO_0009669`
- Open Targets score range: `0` to `0.7917913146926804`
- PubMed records: 4555
- PubMed unique PMIDs: 4555
- PubMed duplicate PMIDs: 0
- PubMed missing `pmid`: 0
- PubMed missing `title`: 12
- PubMed empty `abstract`: 1
- PubMed missing `pub_date`: 0
- PubMed abstract length min/max/avg: 0 / 6062 / 1520.78

## Correctness Assessment

第一阶段目前可以成功运行，且两个主要产物都是合法 JSONL。Open Targets 输出字段完整，PubMed 输出没有重复 PMID，整体上满足“为后续抽取阶段提供 SMA 相关候选文献和外部 gene baseline”的基本目的。

但严格说，本阶段当前只能算“可运行且可用”，还不能算“可稳定复现”。原因是两个脚本都读取实时外部 API，没有固定快照日期、没有记录 API 返回总量/查询参数 manifest，也没有将运行参数写入产物元数据。2026-06-08 重跑后，Open Targets 从旧的 161 条变为 164 条，PubMed 从旧的 1840 条变为 4555 条；这类变化可能来自外部数据源更新，也可能来自旧运行未完整抓取。当前代码无法仅凭产物反推是哪一种。

## Accuracy And Reasonableness

Open Targets:

- 查询 disease ID `MONDO_0009669` 是合理的 SMA disease baseline 入口。
- 当前每条记录都有 gene symbol、target ID 和 score，可作为 gene-disease baseline。
- 代码没有检查 GraphQL `errors` 字段；如果 API 返回部分错误但 HTTP 仍为 200，当前脚本可能把异常状态当作正常结果处理。
- `verify=False` 关闭 HTTPS 证书校验，不适合长期运行。日志中已出现 `InsecureRequestWarning`。

PubMed:

- 查询语句 `"Spinal Muscular Atrophy"[Title/Abstract]` 能稳定抓到 SMA 文献候选，适合作为初始召回。
- 只保留有 `AB` 字段的 MEDLINE 记录，方向合理，但仍出现 1 条空摘要，说明需要额外过滤 `abstract.strip()`。
- 12 条记录没有标题，主要来自 NCBI/MEDLINE 记录本身；这不是致命问题，但后续抽取/展示应能处理空标题。
- `RETMAX=5000` 是硬编码上限；当 PubMed 命中超过 5000 时会静默截断，不适合长期完整采集。
- 未指定日期范围、排序或增量策略，因此每次重跑都可能改变数据集边界。

## Diagnosed Code Issues

1. `src/crawler/api_fetcher.py` uses `verify=False`.
   - Risk: insecure TLS behavior and noisy warnings; can hide certificate/proxy problems.
   - Recommendation: default to certificate verification, make any local proxy exception explicit through an environment variable or CLI flag.

2. Both crawler scripts swallow failures in `main()`.
   - Risk: an exception is logged but process exit code remains successful, so CI or agents may treat a failed crawl as a valid stage.
   - Recommendation: after `logging.exception(...)`, return or raise a non-zero exit code.

3. Both crawler scripts try to install dependencies at runtime.
   - Risk: scripts mutate the environment during data collection, making runs slower and less reproducible.
   - Recommendation: remove `subprocess.check_call([sys.executable, "-m", "pip", "install", ...])` from pipeline code; rely on `requirements.txt`.

4. Outputs are hard-coded and overwritten.
   - Risk: no safe way to produce dated snapshots without manual copying; repeated runs erase the previous canonical data.
   - Recommendation: add CLI options for `--output-file`, `--run-dir`, and possibly `--snapshot-copy`.

5. PubMed crawl lacks snapshot metadata.
   - Risk: large count drift cannot be interpreted after the fact.
   - Recommendation: write a manifest containing query, retmax, batch size, run timestamp, PMID count, parsed abstract count, output hash, and script version/commit.

6. PubMed crawl can include empty abstracts and untitled records.
   - Risk: downstream LLM/NLP extraction may waste calls or produce weak triples.
   - Recommendation: filter empty abstracts and record missing-title counts in manifest.

7. First-stage data changed, but later-stage products remain based on older data.
   - Risk: `data/processed/*` and `data/interim/*` are now stale relative to `data/raw/pubmed_sma_abstracts.jsonl`.
   - Recommendation: treat this as a stage boundary. Do not compare later evaluation metrics to the new stage-1 data until extraction, fusion, analytics, and evaluation are rerun or the old stage-1 snapshot is restored.

## Need For Refinement

需要精进。优先级建议：

1. Add CLI output controls and run manifest generation for both first-stage scripts.
2. Make crawler failures return non-zero exit codes.
3. Remove runtime `pip install` side effects from pipeline scripts.
4. Replace `verify=False` with verified HTTPS by default.
5. Add a small pytest smoke/integration test that mocks API responses and verifies JSONL output shape without touching live external APIs.
6. Add optional live smoke tests under an explicit marker or script so agents do not hit external services accidentally.

## Current Stage Verdict

第一阶段在 2026-06-08 的真实复现结果为成功。产物可用，但不是锁定快照；准确性适合作为初始知识图谱数据源，严谨复现实验和后续论文式指标报告则需要上述精进。当前后续阶段产物应视为基于旧 stage-1 数据的历史结果，不应直接声称它们反映 2026-06-08 这次重跑后的完整流水线结果。

---

# Stage 2 Extraction Reproduction - 2026-06-08

本节按用户指定追加到同一份 reproduction 文档中。第 2 阶段在当前仓库中指：

- LLM relation extraction: `src/extraction/llm_extractor.py`
- Local fallback extraction: `src/extraction/local_pipeline.py`
- Merge raw extraction outputs: `src/extraction/merge_triples.py`

本次诊断使用 `$diagnose` 的反馈环：先保存重跑前产物，再运行可复现的脚本，捕获日志，生成 manifest，检查 JSONL、字段完整性、重复签名、来源分布，以及当前 Stage 1 PubMed 数据与 Stage 2 PMID 的覆盖关系。

## Stage 2 Run Context

- 日期：2026-06-08
- 仓库：`D:\kg_sma_0420`
- Conda 环境：`KG_SMA_env`
- Python：`C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe`
- 运行前已阅读：`docs/agents/PLAN.md`
- 诊断前已阅读：`docs/agents/ISSUE_LOG.md`
- 输入数据：`data/raw/pubmed_sma_abstracts.jsonl`，当前为 4555 条 PubMed 摘要

## Stage 2 Output Convention

第 2 阶段被下游读取的数据本体仍放在：

- `data/processed/llm_extracted_triples.jsonl`
- `data/processed/spacy_extracted_triples.jsonl`
- `data/processed/extracted_triples.jsonl`

本次复现的运行证据放在 dated run 目录：

- `artifacts/runs/stage2_extraction_2026-06-08/`
- `artifacts/runs/stage2_extraction_2026-06-08/README.md`
- `artifacts/runs/stage2_extraction_2026-06-08/llm_extractor_blocked.log`
- `artifacts/runs/stage2_extraction_2026-06-08/local_pipeline.log`
- `artifacts/runs/stage2_extraction_2026-06-08/merge_triples.log`
- `artifacts/runs/stage2_extraction_2026-06-08/manifest.csv`
- `artifacts/runs/stage2_extraction_2026-06-08/field_summary.txt`
- `artifacts/runs/stage2_extraction_2026-06-08/pre_run_outputs/`
- `artifacts/runs/stage2_extraction_2026-06-08/outputs/`

其中 `pre_run_outputs/` 保存重跑前的历史产物，`outputs/` 保存本次重跑后的当前产物快照。

## Stage 2 Commands Run

LLM extractor 没有完整运行，因为本地环境和 `.env` 中均没有真实 `SILICONFLOW_API_KEY`。如果直接运行，脚本会对前 200 篇摘要逐条触发多次失败重试，并可能把历史 LLM 产物覆盖成空或失败产物。因此本次只记录了阻塞原因：

```text
artifacts/runs/stage2_extraction_2026-06-08/llm_extractor_blocked.log
```

实际重跑命令：

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' 'src\extraction\local_pipeline.py'
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' 'src\extraction\merge_triples.py'
```

## Stage 2 Reproduction Results

| Product | Old observed count | Reproduced/current count | JSON validity | SHA-256 |
| --- | ---: | ---: | --- | --- |
| `data/processed/llm_extracted_triples.jsonl` | 674 | 674 historical, not rerun | 0 bad JSON lines | `7b51496237aa674c4c206400678553e8d3efd9fc91916891e1ccb9a5f36d2e2a` |
| `data/processed/spacy_extracted_triples.jsonl` | 1990 | 5101 rerun | 0 bad JSON lines | `cf4e817ae155a536e0bb86321af9fac2b0e8f025aa02d68870a060e2c8422ac7` |
| `data/processed/extracted_triples.jsonl` | 2664 | 5775 rerun merge | 0 bad JSON lines | `4bd82edd85775614bd5758ceb9526f9649244e613eaa8cdc35910f749325a957` |

Additional checks:

- LLM unique PMIDs: 132
- LLM PMIDs present in current PubMed data: 132
- LLM PMIDs in current PubMed first 200 records: 50
- LLM PMIDs in current PubMed records after index 200: 82
- Regex unique PMIDs: 2239
- Regex PMIDs in current PubMed first 200 records: 0
- Regex PMIDs in current PubMed records after index 200: 2239
- Merged unique PMIDs: 2313
- Merged PMIDs in current PubMed first 200 records: 50
- Merged PMIDs in current PubMed records after index 200: 2263
- Merged PMIDs not present in current PubMed data: 0
- Historical LLM records missing `entity_2.name`: 1, at PMID `41257785`
- Regex rerun records missing core fields: 0
- Top merged relations: `ASSOCIATED_WITH_MENTION` 3598, `TREATS_MENTION` 1503, `IMPROVES` 62, `ASSOCIATED_WITH` 39, `TREATS` 33
- Top merged `entity_1` types: `Gene` 3694, `Drug` 1717, `Phenotype` 126, `Protein` 62, `Disease` 41
- Top merged `entity_2` types: `Disease` 5139, `Phenotype` 486, `Drug` 34, `Patient` 17, `Protein` 14

## Stage 2 Correctness Assessment

第 2 阶段当前只能算“部分复现成功”。本地规则抽取和合并脚本运行成功，产物 JSONL 合法，没有重复的阶段签名；新重跑的 Regex 产物没有缺失核心字段。历史 LLM 产物中已有 1 条记录缺失 `entity_2.name`，并随 merge 保留到了当前合并产物中。由于第 1 阶段刚重跑后 PubMed 输入从 1840 条变为 4555 条，本地规则抽取从 1990 条增长到 5101 条是合理的。

但 LLM 抽取没有真实重跑，原因是缺少 `SILICONFLOW_API_KEY`。因此当前 `extracted_triples.jsonl` 是“历史 LLM 产物 + 新重跑 Regex 产物”的兼容合并结果，不应被表述为完整的 2026-06-08 Stage 2 复现结果。

更重要的是，历史 LLM 产物与当前 Stage 1 输入存在边界错位：`llm_extractor.py` 设计上处理当前 PubMed 的 `head(200)`，`local_pipeline.py` 处理 `.iloc[200:]`。但历史 LLM 产物的 132 个唯一 PMID 中，只有 50 个仍位于当前 PubMed 前 200 条，另有 82 个位于当前 200 条之后。也就是说，在没有重跑 LLM 的情况下，当前 merge 同时存在：

- 当前前 200 篇中未被历史 LLM 覆盖的文献。
- 当前 200 条之后被历史 LLM 覆盖、又可能被 Regex 处理的文献。

这不会导致 JSONL 格式错误，但会削弱阶段正确性和指标解释力。

## Stage 2 Accuracy And Reasonableness

LLM extraction:

- 使用 Qwen/Qwen2.5-7B-Instruct 抽取实体和关系，方向合理，适合作为高精度样本来源。
- 只处理前 200 篇摘要，成本可控，但覆盖范围人为且依赖输入排序。
- `computed_confidence = 0.90` 是固定值，不是模型真实置信度。
- Prompt 要求 Gene/Protein/Phenotype/Drug，但历史产物中出现了 `Disease`、`Mutation`、`AnimalModel`、`Treatment`、`Cell`、`Procedure` 等类型，说明模型输出 schema 未被严格校验。
- 没有 key 时脚本只 warning，后续逐条失败，最终仍可能以成功退出码结束，这不适合作为可复现实验。

Local fallback extraction:

- 文件名是 `spacy_extracted_triples.jsonl`，但实际核心是关键词/regex fallback，不是 spaCy NER/RE。
- 规则只覆盖少量 drug/gene/disease 词表，召回集中在 SMN、SMN1、SMN2、nusinersen、risdiplam、zolgensma 等主题，适合作 baseline 或兜底，不适合作主要抽取器。
- 输出关系 `TREATS_MENTION` 和 `ASSOCIATED_WITH_MENTION` 表达的是“同文共现/提及”，不等同于真实治疗或因果关系。
- 因为当前 PubMed 扩大到 4555 条，本地抽取产物增长到 5101 条，量级合理；但其中大量边的语义强度较弱。

Merge:

- 按 `source_pmid + entity_1 + relation + entity_2` 去重，能避免同一文献内完全重复边。
- 不做实体标准化、关系归一、证据文本聚合或来源冲突处理，因此只是 raw extraction merge，不是语义融合。
- 当前 merge 结果混合了历史 LLM 与新 Regex，不能作为完整 Stage 2 重跑的最终科学结论。

## Stage 2 Diagnosed Code Issues

1. `llm_extractor.py` lacks safe run controls.
   - Risk: no `--limit`, `--offset`, `--input-file`, `--output-file`, `--dry-run`, or fixture mode.
   - Recommendation: add CLI arguments so agents can reproduce small slices without overwriting canonical outputs.

2. `llm_extractor.py` handles missing API key too late.
   - Risk: missing key causes per-record retry/failure behavior instead of fast fail before opening the output file.
   - Recommendation: validate `SILICONFLOW_API_KEY` before truncating output and exit non-zero if absent.

3. Stage split depends on current row order.
   - Risk: LLM `head(200)` and Regex `.iloc[200:]` become inconsistent whenever PubMed order changes.
   - Recommendation: write and reuse an explicit PMID split manifest, or drive both scripts from a shared stage-2 input manifest.

4. Local fallback is mislabeled as spaCy.
   - Risk: readers overestimate NLP sophistication and extraction quality.
   - Recommendation: rename output/script documentation toward regex fallback, or implement actual spaCy/model extraction.

5. Fixed confidence values are misleading.
   - Risk: downstream graph weights look quantitative but are hand-assigned constants.
   - Recommendation: rename to `heuristic_confidence` or add a calibrated scoring model.

6. Entity and relation schema is not validated.
   - Risk: LLM can emit out-of-vocabulary types and relations, complicating fusion and evaluation.
   - Recommendation: validate against an ontology/schema and log rejected or normalized outputs.

7. Pipeline scripts still write directly to canonical outputs.
   - Risk: failed or partial runs can overwrite useful historical data.
   - Recommendation: support dated run directories first, then promote outputs to `data/processed/` only after validation.

## Stage 2 Need For Refinement

需要精进，而且应优先精进后再把本阶段作为稳定实验结果使用。优先级建议：

1. Add CLI/config support for input path, output path, offset, limit, model, and run directory.
2. Fail fast and non-zero when `SILICONFLOW_API_KEY` is missing.
3. Generate a Stage 2 split manifest listing exactly which PMIDs are assigned to LLM and Regex.
4. Add schema validation for entity types, relation names, required fields, and JSON parse failures.
5. Rename or redesign `local_pipeline.py` so file names match actual behavior.
6. Add fixture-based tests that mock LLM responses and verify deterministic JSONL output.
7. Only promote run artifacts into canonical `data/processed/` after manifest validation passes.

## Stage 2 Current Verdict

第 2 阶段在 2026-06-08 的复现状态是：Regex fallback 和 merge 成功重跑，LLM 抽取因缺少 `SILICONFLOW_API_KEY` 未能忠实复现。当前 `data/processed/extracted_triples.jsonl` 可作为工程上的兼容中间产物继续探索，但不能作为完整 Stage 2 复现实验结果或最终准确性结论。若要严谨推进，应先修复 LLM fast-fail、输出目录参数化、PMID split manifest 和 schema validation，然后在有 key 的环境中完整重跑。
