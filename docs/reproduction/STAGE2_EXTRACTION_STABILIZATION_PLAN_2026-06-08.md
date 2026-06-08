# Stage 2 Extraction Stabilization Plan - 2026-06-08

本文档评估当前 Stage 2 的状态、可行性和下一步方案。目标不是临时把一次运行补过去，而是在不改 Stage 3 的前提下，让 Stage 2 能稳定、可恢复、可审计地产生下游可读的 `data/processed/extracted_triples.jsonl`。

## Current State

Stage 2 当前包含三个脚本：

- `src/extraction/llm_extractor.py`
- `src/extraction/local_pipeline.py`
- `src/extraction/merge_triples.py`

Stage 3 当前入口是：

- `src/fusion/dictionary_mapper.py`

Stage 3 只读取：

- `data/processed/extracted_triples.jsonl`

因此 Stage 2 可以重构内部运行方式，但最终交付给 Stage 3 的 canonical output 必须保持 JSONL schema：

```json
{
  "source_pmid": "PMID",
  "entity_1": {"name": "string", "type": "string"},
  "relation": "string",
  "entity_2": {"name": "string", "type": "string"},
  "computed_confidence": 0.9,
  "extracted_by": "string"
}
```

当前 canonical 状态：

- `data/processed/llm_extracted_triples.jsonl`: 历史 LLM 产物，674 条，132 个唯一 PMID。
- `data/processed/spacy_extracted_triples.jsonl`: 已基于新 Stage 1 PubMed 数据重跑，5101 条。
- `data/processed/extracted_triples.jsonl`: 已用历史 LLM + 新 Regex 合并，5775 条。

当前额外实验状态：

- SiliconFlow API key 可用，smoke call 成功。
- `Qwen/Qwen2.5-7B-Instruct` 和 `Pro/Qwen/Qwen2.5-7B-Instruct` 在本任务中大量输出坏 JSON 或重复 token，不适合作为稳定复现模型。
- `Qwen/Qwen2.5-72B-Instruct` 小样本表现明显更好：前 5 篇输出 19 条 triples，0 个 malformed JSON。
- `Qwen/Qwen2.5-72B-Instruct` 串行完整跑 200 篇耗时较长，中断前 `.tmp` 已写出 621 条、107 个唯一 PMID，但没有完整 checkpoint/resume，因此不能直接作为正式完成产物。

## Why Stage 2 Is Blocked

阻塞不是密钥问题，也不是 Stage 3 接口问题。真正阻塞点有四个：

1. LLM 输出质量不可控。
   - 7B 模型即使使用 JSON mode，也会返回坏 JSON、重复 token、非 schema 字段。
   - 这导致 Stage 2 的 pass/fail 信号不稳定。

2. LLM 运行不可恢复。
   - 当前逻辑是单进程处理前 200 篇。
   - 中断后无法可靠区分“已处理但无 triple”和“未处理”。
   - `.tmp` 里的部分结果不能直接无脑续跑合并。

3. Canonical output 保护不足。
   - 原始脚本会先打开正式输出文件写入，失败或超时可能留下空文件。
   - 已经通过实验性修改验证了“先写临时文件，成功后替换”是必要保护。

4. Stage 2 split 依赖当前行号。
   - LLM 默认处理 `head(200)`。
   - Regex 默认处理 `.iloc[200:]`。
   - Stage 1 重跑后 PubMed 排序变化会导致历史 LLM 产物和新 Regex 产物错位。

## Feasibility Assessment

### Full Refactor

内容：

- 新建 Stage 2 orchestration layer。
- 抽象 extractor interface。
- 统一 schema validator、manifest writer、chunk runner、promotion flow。
- 重命名 `spacy_extracted_triples.jsonl` 为 regex 语义，同时同步 Stage 3 和所有文档。

优点：

- 长期最干净。
- 能消除命名、运行、校验、输出治理问题。

缺点：

- 改动面较大。
- 容易波及 Stage 3、evaluation 和历史报告。
- 当前最迫切的问题是复现与稳定交付，full refactor 的收益会被范围扩大抵消。

结论：现在不推荐作为第一步。

### Durable Small Upgrade

内容：

- 保留 Stage 3 输入路径和 schema 不变。
- 保留三个已有 Stage 2 脚本的职责边界。
- 给 LLM 抽取增加正式的 chunk/resume/validate/promote 机制。
- 给 Regex 和 Merge 增加 run artifact 与 validation，而不是重命名或大拆分。

优点：

- 不改变 Stage 3。
- 能解决真实阻塞：长运行、坏 JSON、输出覆盖、不可恢复。
- 改动可测试、可分步提交。

缺点：

- `spacy_extracted_triples.jsonl` 这个历史命名暂时保留，语义不完美。
- LLM 和 Regex 的抽取质量本身仍需要后续评估增强。

结论：推荐。

## Recommended Decision

推荐采用“Durable Small Upgrade”，不是临时补丁，也不是全量重构。

核心原则：

1. Stage 3 contract 不变。
2. Stage 2 内部增加稳定运行层。
3. Canonical outputs 只在验证通过后 promotion。
4. LLM 复现以 chunk 为最小可恢复单位。
5. 模型从 `Qwen/Qwen2.5-7B-Instruct` 切换到 `Qwen/Qwen2.5-72B-Instruct`，因为 7B 在当前复现实验中不能稳定产出可解析 JSON。

## Target Run Layout

每次完整 Stage 2 运行输出到：

```text
artifacts/runs/stage2_extraction_full_YYYY-MM-DD_HHMM/
  README.md
  stage2_input_split.json
  manifest.csv
  validation_summary.json
  logs/
    llm_chunk_000_019.log
    llm_chunk_020_039.log
    regex.log
    merge.log
  chunks/
    llm_000_019.jsonl
    llm_020_039.jsonl
  outputs/
    data/processed/llm_extracted_triples.jsonl
    data/processed/spacy_extracted_triples.jsonl
    data/processed/extracted_triples.jsonl
  rejected/
    malformed_llm_outputs.jsonl
    invalid_triples.jsonl
```

Canonical promotion 只发生在 validation 通过后：

```text
data/processed/llm_extracted_triples.jsonl
data/processed/spacy_extracted_triples.jsonl
data/processed/extracted_triples.jsonl
```

## Stage 2 Split Contract

必须显式写入 `stage2_input_split.json`，不要再隐式依赖 dataframe 行号：

```json
{
  "input_file": "data/raw/pubmed_sma_abstracts.jsonl",
  "input_sha256": "...",
  "llm_pmids": ["... first 200 pmids ..."],
  "regex_pmids": ["... remaining pmids ..."],
  "llm_model": "Qwen/Qwen2.5-72B-Instruct",
  "chunk_size": 20
}
```

这样以后即使 PubMed 重新排序，也能明确知道某次 Stage 2 复现覆盖的是哪组 PMID。

## Validation Rules

Promotion 前必须通过：

- JSONL 全部可解析。
- 每条 triple 必须有 `source_pmid`。
- `entity_1.name`、`entity_1.type`、`relation`、`entity_2.name`、`entity_2.type` 不得为空。
- `computed_confidence` 必须是数字。
- `extracted_by` 必须包含 `LLM` 或等于 `Regex_Fallback`。
- merged output 不得有重复签名：`source_pmid + entity_1.name + relation + entity_2.name`。
- Stage 3 dry-run 能读完 `data/processed/extracted_triples.jsonl` 或 run output 中的 candidate merged file。

建议暂时只做 schema validation，不在本轮强制做 ontology validation。原因是 ontology validation 会引入更大的领域判断，容易把“稳定复现”扩大成“医学抽取质量重构”。

## Model Policy

推荐本轮使用：

- `Qwen/Qwen2.5-72B-Instruct`
- `response_format={"type": "json_object"}`
- `temperature=0.0`
- chunk size: 20 PMIDs

不推荐继续使用：

- `Qwen/Qwen2.5-7B-Instruct`
- `Pro/Qwen/Qwen2.5-7B-Instruct`

原因：

- 7B 系列在当前实验中有大量 malformed JSON。
- 72B 小样本和部分长跑结果更稳定。

注意：模型切换会改变实验口径。文档和 `extracted_by` 必须记录真实 model id，不能再硬编码 `LLM_Qwen2.5_7B`。

## Implementation Plan

### Step 1 - Stabilize LLM extractor

修改 `src/extraction/llm_extractor.py`：

- 从 `.env` 或环境变量读取 `SILICONFLOW_API_KEY`。
- 缺 key 时 fast-fail，返回非零退出码。
- 支持 `--input-file`、`--output-file`、`--offset`、`--limit`、`--model`、`--max-tokens`、`--min-triples`。
- 使用 temp output，成功后 replace。
- 使用 `response_format={"type": "json_object"}`。
- `extracted_by` 写真实 model id。
- 记录 malformed count 和 failed count。

### Step 2 - Add chunk runner

新增一个 Stage 2 runner，例如：

- `src/extraction/run_stage2_extraction.py`

职责：

- 读取 Stage 1 PubMed JSONL。
- 生成固定 PMID split manifest。
- 按 chunk 调用 LLM extractor。
- 已存在且验证通过的 chunk 自动跳过。
- 每个 chunk 独立日志和输出。
- 合并 LLM chunks 到 run output，不直接写 canonical。

### Step 3 - Validate run outputs

新增或内置 validator：

- 校验 LLM chunk outputs。
- 校验 Regex output。
- 校验 merged output。
- 输出 `validation_summary.json` 和 `manifest.csv`。

### Step 4 - Promote only after validation

Runner 在所有 validation 通过后，将 run output 复制到 canonical `data/processed/`。

如果 validation 失败：

- 保留 run artifacts。
- 不替换 canonical outputs。
- 写明失败原因。

### Step 5 - Verify Stage 3 compatibility

不改 Stage 3 代码。只做兼容性验证：

```powershell
python src/fusion/dictionary_mapper.py
```

如果只想 dry-run，可先让 validator 读取 candidate `outputs/data/processed/extracted_triples.jsonl` 验证 schema。

## Acceptance Criteria

本轮完成的定义：

- Stage 2 full run directory 存在，并包含 split、chunks、logs、manifest、validation summary。
- `data/processed/llm_extracted_triples.jsonl` 是完整、验证通过的本轮 LLM 输出，不是历史 LLM 输出。
- `data/processed/spacy_extracted_triples.jsonl` 是本轮 Regex 输出。
- `data/processed/extracted_triples.jsonl` 是本轮 LLM + Regex merge 输出。
- Stage 3 `dictionary_mapper.py` 能无代码改动读取新的 `extracted_triples.jsonl`。
- reproduction 文档记录模型、chunk size、counts、hashes、失败/拒绝数量。

## Open Discussion Question 1

是否确认本轮采用推荐方案：

> 保留 Stage 3 contract 不变，对 Stage 2 做 durable small upgrade，引入 chunk/resume/validate/promote；LLM 模型切换为 `Qwen/Qwen2.5-72B-Instruct`，并把模型切换作为正式实验口径记录。

我的推荐答案：确认。

理由：它直接解决当前阻塞，不把 7B 的坏 JSON 问题伪装成可复现结果，也不会把 full refactor 的风险带入 Stage 3。

如果不同意，需要在两个替代方向中选择一个：

- 继续坚持 7B：成本低但复现可行性差，预计要投入 prompt repair / retry repair / JSON extraction fallback，质量仍不稳定。
- 做 full refactor：长期更干净，但本轮范围会明显扩大，并且更容易影响 Stage 3 和 evaluation。
