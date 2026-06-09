# SMA Graph RAG 与关系冲突裁决实施计划

Status: Pending user confirmation
Created: 2026-06-10
Branch: `feature/huawei-ai应用工程师-ai技术应用/graph-rag-conflict-prd-plan-20260609-225214`

## 核心原则

本功能采用清晰的职责分工：

- 本地检索负责“找证据”。
- 大模型负责“理解证据、生成答案、裁决冲突”。

这意味着本地代码必须先从 PubMed 摘要、aligned triples、fused triples、关系冲突文件、
图谱指标和可选 Neo4j 邻域中构造可审计的 Evidence Context；大模型只能消费这个
Evidence Context，不允许跳过检索直接凭通用知识回答，也不允许在没有证据的情况下
补充医学结论。

## 目标

围绕当前 SMA 知识图谱构建两个可演示的 AI 应用能力：

1. SMA Graph RAG 智能问答。
2. LLM 辅助关系冲突裁决。

二者共享同一个 Evidence Context 层，以体现一个完整 AI 应用系统的工程设计，而不是
两个互不相关的脚本。

## 当前输入基线

本计划不重跑 Stage 1-4，直接消费当前 canonical outputs：

- PubMed 摘要：`data/raw/pubmed_sma_abstracts.jsonl`，4554 条。
- Stage 2 LLM-only triples：`data/processed/extracted_triples.jsonl`，18288 条。
- Stage 3 aligned triples：`data/interim/aligned_triples.jsonl`，18288 条。
- Stage 3 fused graph：`data/processed/fused_triples.jsonl`，11155 条。
- Stage 3 relation conflicts：`data/interim/relation_conflicts.jsonl`，59 条。
- Stage 4 analytics：`data/processed/analytics_metrics.csv`，6648 行。

## 总体架构

```text
Local Evidence Retrieval
  |
  |-- PubMed abstract loader
  |-- aligned triple loader
  |-- fused edge loader
  |-- conflict loader
  |-- lexical/entity retrieval
  |-- optional embedding retrieval
  |-- optional Neo4j neighborhood expansion
  v
Evidence Context
  |
  |-- Graph RAG answer context
  |-- Conflict adjudication context
  v
LLM Reasoning Layer
  |
  |-- evidence-grounded answer generation
  |-- conflict classification and rationale
  v
Auditable Outputs
  |
  |-- answer JSON / Markdown
  |-- adjudication JSONL
  |-- manifest.csv
  |-- validation_summary.json
```

## 模块边界

### 本地检索层

职责：

- 读取本地 canonical 数据。
- 根据问题、实体名、关系类型、PMID、图邻域找到候选证据。
- 对候选证据排序、截断、去重。
- 构造 Evidence Context。
- 输出检索理由、PMID、evidence text、三元组、图边、review status、confidence。

禁止：

- 调用大模型补充证据。
- 在没有源 PMID 或 evidence text 的情况下构造事实证据。
- 修改 canonical graph 文件。

### 大模型理解层

职责：

- 只基于 Evidence Context 生成答案。
- 只基于 Evidence Context 裁决关系冲突。
- 输出结构化 JSON，包含结论、引用 PMID、置信度、限制和理由。
- 当证据不足时明确回答“证据不足”。

禁止：

- 绕过 Evidence Context 自行检索。
- 使用模型常识新增未检索到的医学事实。
- 直接改写 `data/processed/fused_triples.jsonl`。

## Phase 0：确认方案与分支策略

执行前确认：

- V1 是否保持 CLI-first。
- V1 是否不修改 canonical graph。
- 大模型默认是否继续使用 SiliconFlow `deepseek-ai/DeepSeek-V4-Flash`。
- Neo4j 是否仅作为可选增强，不作为 dry-run 依赖。
- 是否先执行 Phase 1 + Phase 2，再进入 Graph RAG 回答生成。

退出标准：

- 用户明确确认上述选择。

## Phase 1：Evidence Context 本地证据层

新增文件：

- `src/evidence/__init__.py`
- `src/evidence/loaders.py`
- `src/evidence/context_builder.py`
- `tests/unit/test_evidence_context.py`

核心能力：

- 按 PMID 加载 PubMed 摘要。
- 按实体对和关系加载 aligned triples。
- 按实体对、实体名、关系加载 fused graph edges。
- 读取 relation conflicts。
- 将证据统一成 Evidence Context。
- 限制上下文大小，避免 LLM prompt 超长。
- 输出缺失证据报告，例如 missing abstract、missing aligned triple。

Evidence Context 最小结构：

```json
{
  "context_id": "string",
  "purpose": "graph_rag_answer | conflict_adjudication",
  "query": "string",
  "entities": [],
  "abstracts": [],
  "aligned_triples": [],
  "fused_edges": [],
  "conflicts": [],
  "supporting_pmids": [],
  "missing_evidence": [],
  "limits": {}
}
```

验证：

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

退出标准：

- 单元测试覆盖摘要加载、实体对证据加载、上下文截断、缺失证据报告。
- 不依赖 LLM，不依赖 Neo4j。

## Phase 2：关系冲突裁决 dry-run

新增文件：

- `src/fusion/adjudicate_relation_conflicts.py`
- `tests/unit/test_conflict_adjudication.py`

本地检索职责：

- 读取 59 条 `relation_conflicts.jsonl`。
- 对每个冲突实体对，从 aligned triples 中找出所有相关证据。
- 关联 PubMed 摘要和 evidence text。
- 生成 conflict adjudication Evidence Context。
- 在 dry-run 下输出待裁决 payload，不调用大模型。

大模型职责：

- 此阶段暂不启用，只定义后续 live mode 所需输入格式。

输出：

- `artifacts/runs/conflict_adjudication_<timestamp>/payloads.jsonl`
- `artifacts/runs/conflict_adjudication_<timestamp>/manifest.csv`
- `artifacts/runs/conflict_adjudication_<timestamp>/validation_summary.json`

验证：

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/fusion/adjudicate_relation_conflicts.py --dry-run --run-dir artifacts/runs/conflict_adjudication_probe_<timestamp>
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

退出标准：

- dry-run 产出 59 个 payload。
- 每个 payload 都包含实体对、冲突关系、相关 aligned triples、PMID 和摘要引用。
- canonical `data/processed/fused_triples.jsonl` 不变化。

## Phase 3：关系冲突 LLM 裁决 live mode

扩展文件：

- `src/fusion/adjudicate_relation_conflicts.py`

本地检索职责：

- 复用 Phase 2 的 payload。
- 控制每次传给大模型的 evidence context 大小。
- 对缺失证据的冲突直接标记为 `insufficient_evidence`，不浪费 LLM 调用。

大模型职责：

- 根据 evidence context 对冲突分类：
  - `supported_context_dependent`
  - `extraction_error`
  - `direction_error`
  - `relation_normalization_issue`
  - `real_conflict_needs_human_review`
  - `insufficient_evidence`
- 输出 retained relations、rejected relations、rationale、confidence、supporting PMIDs。

输出：

- `adjudications.jsonl`
- `unresolved.jsonl`
- `rejected_or_failed.jsonl`
- `validation_summary.json`
- `manifest.csv`

验证：

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/fusion/adjudicate_relation_conflicts.py --limit 3 --run-dir artifacts/runs/conflict_adjudication_live_probe_<timestamp>
```

退出标准：

- live probe 至少处理 3 个冲突。
- LLM JSON 解析失败、API 失败、证据不足都进入可审计输出。
- 不修改 canonical graph。

## Phase 4：Graph RAG 本地检索核心

新增文件：

- `src/qa/__init__.py`
- `src/qa/retriever.py`
- `src/qa/build_index.py`
- `tests/unit/test_graph_rag_retrieval.py`

本地检索职责：

- 基于 PubMed abstracts、aligned triples、fused edges 构建可检索语料。
- 第一版先实现 lexical/entity retrieval。
- 可选实现 sentence-transformers embedding retrieval。
- 可选接入 Neo4j graph neighborhood expansion。
- 返回 Graph RAG Evidence Context。

大模型职责：

- 此阶段不生成答案，只消费检索结果的结构定义。

索引原则：

- 索引 manifest 必须记录输入文件 hash、记录数、生成时间、检索模式。
- 不把向量索引误认为 canonical pipeline output。
- 索引可以重建，不作为唯一事实来源。

验证：

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/qa/build_index.py --run-dir artifacts/runs/graph_rag_index_probe_<timestamp>
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

退出标准：

- 五个固定问题均能检索到非空 Evidence Context。
- 无 LLM、无 Neo4j 时也能完成检索 dry-run。

## Phase 5：Graph RAG 大模型答案生成

新增文件：

- `src/qa/answer.py`
- `src/qa/run_graph_rag.py`
- `tests/unit/test_graph_rag_answer_schema.py`

本地检索职责：

- 接收用户问题。
- 调用 retriever 生成 Evidence Context。
- 将 Evidence Context 压缩成 LLM prompt 输入。
- 输出 dry-run evidence package。

大模型职责：

- 只基于 Evidence Context 生成答案。
- 必须引用 PMID。
- 必须列出 supporting triples。
- 必须输出 limitations。
- 证据不足时不能硬答。

输出结构：

```json
{
  "question": "string",
  "answer": "string",
  "supporting_pmids": [],
  "supporting_triples": [],
  "graph_context": [],
  "limitations": [],
  "model": "deepseek-ai/DeepSeek-V4-Flash",
  "retrieval": {}
}
```

验证：

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/qa/run_graph_rag.py --question "How does Nusinersen affect motor function?" --dry-run
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

退出标准：

- dry-run 输出证据包。
- live mode 输出带 PMID 的答案。
- prompt 明确禁止模型使用 Evidence Context 外的事实。

## Phase 6：演示与文档

更新文件：

- `README.md`
- `docs/reproduction/GRAPH_RAG_CONFLICT_ADJUDICATION_<date>.md`
- 必要时新增项目 handoff。

演示内容：

- Graph RAG 五个问题：
  - `What is known about SMN1 in SMA?`
  - `How does Nusinersen affect motor function?`
  - `What evidence links SMN protein to motor neuron degeneration?`
  - `Are there contradictory findings for Onasemnogene Abeparvovec?`
  - `Which genes are strongly connected to Spinal Muscular Atrophy?`
- 关系冲突 dry-run 一个完整样例。
- 若 API key 可用，补一个 live LLM 回答和一个 live conflict adjudication 样例。

验证：

- unit tests 通过。
- Graph RAG dry-run 可复现。
- conflict adjudication dry-run 可复现。
- 检查 diff 中没有 `.env`、API key、Neo4j password。

## 验收标准

整体 v1 完成时，应满足：

- 本地检索可独立运行，负责找证据。
- 大模型调用可选，负责理解、生成、裁决。
- 没有大模型调用时，仍能演示 evidence retrieval 和 conflict payload。
- Graph RAG answer 必须带 PMID 或明确证据不足。
- Conflict adjudication 必须输出结构化裁决结果或 unresolved 原因。
- 所有新运行产物写入 `artifacts/runs/`。
- canonical graph 不被自动修改。
- 单元测试覆盖新增核心逻辑。

## 风险与控制

- 风险：大模型幻觉。
  - 控制：Evidence Context-only prompt、PMID 引用、limitations 字段、证据不足显式返回。
- 风险：检索召回不足。
  - 控制：lexical/entity retrieval + optional embedding retrieval + optional graph expansion。
- 风险：Neo4j 不可用。
  - 控制：Graph RAG 与 conflict dry-run 必须基于本地 JSONL 独立运行。
- 风险：裁决结果过早污染 canonical graph。
  - 控制：v1 只写独立 adjudication artifact，不 promote。
- 风险：向量索引依赖过重。
  - 控制：先做本地 lexical/entity baseline，embedding retrieval 作为增强。

## 请用户确认

推荐确认项：

- V1 采用 CLI-first。
- 本地检索层负责找证据，大模型层只消费证据。
- Phase 1 + Phase 2 先执行，先做 Evidence Context 和 conflict dry-run。
- Graph RAG 的 live LLM answer 放在 Phase 5。
- V1 不修改 canonical graph。

确认后执行顺序：

1. Phase 1：Evidence Context 本地证据层。
2. Phase 2：关系冲突裁决 dry-run。
3. Phase 3：可选 live LLM 冲突裁决。
4. Phase 4：Graph RAG 本地检索核心。
5. Phase 5：Graph RAG 大模型答案生成。
6. Phase 6：演示与文档。
