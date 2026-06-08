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
