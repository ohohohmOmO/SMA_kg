# SMA Knowledge Graph Project Handoff Snapshot - 2026-06-08

Snapshot date: 2026-06-08.

This document records the repository state as of 2026-06-08. It is reference
material, not a live preflight checklist. For current operating rules, read
`AGENTS.md` and `docs/agents/PLAN.md`.

本文档基于当前仓库中的真实源码、数据产物和历史运行输出整理，不依赖
`README.md`、`SMA_KG_Project_Overview.md` 或旧技术概述的描述。目标是让新
开发者或 agent 能快速理解项目已经开发到哪里、每个阶段如何实现、产物在哪、
效果如何，以及接手时应该先看哪些文件。

## 1. 当前项目定位

本仓库正在开发一个面向 Spinal Muscular Atrophy, SMA 的知识图谱构建管线。
它把两类来源转成结构化知识：

- Open Targets 中的 SMA gene-disease association baseline。
- PubMed 中与 SMA 相关的文献摘要。

最终目标是形成可分析、可入库、可可视化的 biomedical knowledge graph。图谱
中的核心边来自文献抽取的三元组：

```text
entity_1 -- relation --> entity_2
```

实体类型包括 `Gene`、`Protein`、`Drug`、`Disease`、`Phenotype` 等，实际产
物中还出现了 `Treatment`、`Patient`、`Mutation`、`Cell`、`AnimalModel` 等
LLM 扩展出来的类型。

## 2. 接手前必须知道的运行规则

- 先读 `docs/agents/PLAN.md`。
- 使用 conda 环境 `KG_SMA_env`。
- 出现运行错误时先读 `docs/agents/ISSUE_LOG.md`。
- 如果成功解决问题，把症状、原因、修复和验证结果追加到 `docs/agents/ISSUE_LOG.md`。

当前已验证环境：

```powershell
conda activate KG_SMA_env
python --version
```

当前 Python 版本为 `3.13.5`。依赖清单在根目录 `requirements.txt`，该文件已
按源码实际 import 补充了图谱、LLM、NLP 和可视化依赖。

外部环境变量：

- `SILICONFLOW_API_KEY`: LLM 抽取和 LLM 评估需要。
- `NEO4J_URI`: Neo4j 连接地址，默认代码使用 `bolt://localhost:7687`。
- `NEO4J_USER`: Neo4j 用户名，默认 `neo4j`。
- `NEO4J_PASSWORD`: Neo4j 密码。
- `HF_ENDPOINT`: HuggingFace 下载端点，代码中常设为 `https://hf-mirror.com`。

## 3. 整理后的仓库结构

```text
D:\kg_sma_0420
|-- AGENTS.md
|-- requirements.txt
|-- artifacts/
|   |-- README.md
|   |-- reports/
|   |-- test-results/
|-- data/
|   |-- raw/
|   |-- external/
|   |-- interim/
|   |-- processed/
|-- docs/
|   |-- PROJECT_HANDOFF_2026-06-08.md
|   |-- agents/
|   |-- archive/
|   |-- graph_viewer.html
|   |-- agents/
|-- lib/
|   |-- bindings/
|   |-- tom-select/
|   |-- vis-9.1.2/
|-- notebooks/
|-- src/
|   |-- crawler/
|   |-- extraction/
|   |-- fusion/
|   |-- database/
|   |-- evaluation/
```

整理动作：

- 根目录历史 `.txt` 输出已移到 `artifacts/reports/`。
- 根目录 Open Targets 测试响应 `ot_test_result.json` 已移到
  `artifacts/test-results/`。
- `data/` 下的流水线产物保留原位，因为源码按这些路径读取。
- `docs/graph_viewer.html` 保留原位，因为它是当前图谱可视化出口。

## 4. 总体流水线

```text
Open Targets API
  -> data/external/sma_gda_baseline.jsonl

PubMed Entrez
  -> data/raw/pubmed_sma_abstracts.jsonl
  -> LLM extraction + regex fallback extraction
  -> data/processed/llm_extracted_triples.jsonl
  -> data/processed/spacy_extracted_triples.jsonl
  -> data/processed/extracted_triples.jsonl
  -> dictionary mapping
  -> data/interim/mapped_triples.jsonl
  -> semantic alignment
  -> data/interim/aligned_triples.jsonl
  -> evidence aggregation
  -> data/processed/fused_triples.jsonl
  -> Neo4j import / NetworkX analytics / PyVis visualization / evaluation
```

## 5. 当前产物规模

| 产物 | 行数 | 说明 |
| --- | ---: | --- |
| `data/raw/pubmed_sma_abstracts.jsonl` | 1840 | PubMed SMA 摘要 |
| `data/external/sma_gda_baseline.jsonl` | 161 | Open Targets SMA gene baseline |
| `data/processed/llm_extracted_triples.jsonl` | 674 | Qwen LLM 抽取三元组 |
| `data/processed/spacy_extracted_triples.jsonl` | 1990 | 本地规则兜底抽取三元组 |
| `data/processed/extracted_triples.jsonl` | 2664 | 合并去重后的原始抽取结果 |
| `data/interim/mapped_triples.jsonl` | 2664 | 词典标准化后的中间结果 |
| `data/interim/aligned_triples.jsonl` | 2664 | 语义对齐后的中间结果 |
| `data/processed/fused_triples.jsonl` | 652 | 融合后的唯一图谱边 |
| `data/processed/analytics_metrics.csv` | 844 | 图实体 PageRank 和社区结果 |
| `data/processed/human_evaluation_sample.csv` | 101 | 人工评估样本表，含表头 |
| `data/processed/human_evaluation_sample_scored.csv` | 102 | 已打分人工评估表，含表头 |
| `data/processed/llm_novel_discoveries.csv` | 11 | 新颖候选关系表，含表头 |

## 6. 阶段 1: 数据获取

### 6.1 Open Targets baseline

看这些文件：

- 源码：`src/crawler/api_fetcher.py`
- 测试脚本：`tests/smoke/test_opentargets_api.py`
- 测试响应：`artifacts/test-results/ot_test_result.json`
- 产物：`data/external/sma_gda_baseline.jsonl`

实现方法：

- `api_fetcher.py` 使用 `requests.post` 调用 Open Targets GraphQL API。
- API 地址是 `https://api.platform.opentargets.org/api/v4/graphql`。
- 默认疾病 ID 是 `MONDO_0009669`。
- 查询字段是 disease associated targets，包括 target ID、approved symbol 和
  association score。
- `fetch_page()` 使用 `tenacity` 做指数退避重试。
- 分页大小 `size = 1000`。
- 输出 JSONL 字段：
  - `disease_id`
  - `gene_symbol`
  - `target_id`
  - `score`

当前效果：

- baseline 产物有 161 行。
- 前几条包括 `SMN1`、`SMN2`、`NAIP` 等 SMA 相关基因。

注意点：

- `api_fetcher.py` 中 `requests.post(..., verify=False)` 关闭了证书校验。
- `tests/smoke/test_opentargets_api.py` writes its response to
  `artifacts/test-results/ot_test_result.json`.

### 6.2 PubMed 文献摘要

看这些文件：

- 源码：`src/crawler/pubmed_crawler.py`
- 产物：`data/raw/pubmed_sma_abstracts.jsonl`

实现方法：

- 使用 `Bio.Entrez` 和 `Bio.Medline`。
- 搜索式是 `"Spinal Muscular Atrophy"[Title/Abstract]`。
- `RETMAX = 5000`，但当前实际保存了 1840 条含摘要记录。
- `BATCH_SIZE = 200`。
- 每批请求后 `time.sleep(0.35)`，用于降低 NCBI 请求压力。
- 输出 JSONL 字段：
  - `pmid`
  - `title`
  - `abstract`
  - `pub_date`

当前效果：

- 原始摘要文件有 1840 行。
- 当前数据包含 2026 年左右较新的 SMA 论文摘要。

注意点：

- `Entrez.email` 当前写死为 `kg_sma_builder@example.com`。正式长期使用时应换
  成真实维护者邮箱。

## 7. 阶段 2: 知识抽取

### 7.1 LLM 抽取

看这些文件：

- 源码：`src/extraction/llm_extractor.py`
- 输入：`data/raw/pubmed_sma_abstracts.jsonl`
- 输出：`data/processed/llm_extracted_triples.jsonl`

实现方法：

- 使用 `openai` Python SDK，但 `base_url` 指向 SiliconFlow：
  `https://api.siliconflow.cn/v1`。
- 模型是 `Qwen/Qwen2.5-7B-Instruct`。
- 系统提示要求模型只输出 JSON，格式为：

```json
{
  "triples": [
    {
      "entity_1": {"name": "Zolgensma", "type": "Drug"},
      "relation": "IMPROVES",
      "entity_2": {"name": "motor function", "type": "Phenotype"}
    }
  ]
}
```

- `call_llm_extraction()` 使用 `tenacity` 重试。
- 主流程只处理 `head(200)`，也就是前 200 篇摘要。
- 每个输出三元组统一补充：
  - `source_pmid`
  - `computed_confidence = 0.90`
  - `extracted_by = LLM_Qwen2.5_7B`

当前效果：

- 当前 LLM 抽取产物 674 行。
- 例子：`Onasemnogene Abeparvovec TREATS spinal muscular atrophy type I`。

注意点：

- 如果没有 `SILICONFLOW_API_KEY`，脚本会 warning，实际 API 调用会失败。
- 代码会清理 LLM 偶尔输出的 markdown code fence。
- Prompt 声称只抽取 Genes、Proteins、Phenotypes、Drugs，但实际产物中出现
  `Treatment`、`Patient`、`Procedure` 等类型，后续 schema 需要收紧或接受扩展。

### 7.2 本地规则兜底抽取

看这些文件：

- 源码：`src/extraction/local_pipeline.py`
- 输入：`data/raw/pubmed_sma_abstracts.jsonl`
- 输出：`data/processed/spacy_extracted_triples.jsonl`

实现方法：

- 文件会 import `spacy`，但当前核心抽取逻辑是 `regex_fallback_extraction()`。
- 词表：
  - drugs: `nusinersen`, `risdiplam`, `zolgensma`, `spinraza`, `evrysdi`,
    `onasemnogene abeparvovec`
  - genes: `smn1`, `smn2`, `smn`, `exon 7`
  - diseases: `spinal muscular atrophy`, `sma`
- 主流程读取原始摘要的 `.iloc[200:]`，也就是跳过前 200 篇，与 LLM 阶段互补。
- 如果 drug 和 disease 同时出现，生成 `TREATS_MENTION`。
- 如果 gene 和 disease 同时出现，生成 `ASSOCIATED_WITH_MENTION`。
- confidence 分别是 0.75 和 0.70。
- `extracted_by = Regex_Fallback`。

当前效果：

- 当前本地兜底产物 1990 行。

注意点：

- 文件名叫 `spacy_extracted_triples.jsonl`，但实际主要不是 spaCy NER，而是规则
  匹配。后续命名可考虑改为 `regex_extracted_triples.jsonl`，但改名需要同步下游
  `merge_triples.py`。

### 7.3 合并抽取结果

看这些文件：

- 源码：`src/extraction/merge_triples.py`
- 输入：
  - `data/processed/llm_extracted_triples.jsonl`
  - `data/processed/spacy_extracted_triples.jsonl`
- 输出：`data/processed/extracted_triples.jsonl`

实现方法：

- 按 `pmid + entity_1 + relation + entity_2` 构造签名去重。
- 保留原三元组 JSON 结构。

当前效果：

- 合并后 2664 行，正好等于 674 + 1990，说明当前两路产物没有被签名去重掉。

## 8. 阶段 3: 知识融合

### 8.1 词典标准化

看这些文件：

- 源码：`src/fusion/dictionary_mapper.py`
- 输入：`data/processed/extracted_triples.jsonl`
- 输出：`data/interim/mapped_triples.jsonl`

实现方法：

- 内置 `DICTIONARY`，按实体 type 和小写 name 做标准化。
- 当前覆盖 drug、disease、gene。
- 典型映射：
  - `spinraza` -> `Nusinersen`
  - `evrysdi` -> `Risdiplam`
  - `zolgensma`、`oa` -> `Onasemnogene Abeparvovec`
  - `sma` -> `Spinal Muscular Atrophy`
  - `smn1` -> `SMN1`
  - `exon 7` -> `SMN2 (Exon 7)`

当前效果：

- 输入 2664 行，输出 2664 行。

### 8.2 语义对齐

看这些文件：

- 源码：`src/fusion/semantic_aligner.py`
- 输入：`data/interim/mapped_triples.jsonl`
- 输出：`data/interim/aligned_triples.jsonl`

实现方法：

- 按实体类型收集实体名称。
- 使用 `SentenceTransformer('all-MiniLM-L6-v2')` 编码实体名称。
- 使用 `sklearn.metrics.pairwise.cosine_similarity` 计算相似度。
- 相似度阈值为 `0.88`。
- 用一个简单 connected-component 风格聚类把相似实体归到 canonical name。
- canonical name 选择频次最高者，频次相同时按字母序稳定选择。
- 如果 HuggingFace 下载失败，脚本会直接复制 mapped 文件到 aligned 文件，跳过
  fuzzy semantic alignment。

当前效果：

- 输入 2664 行，输出 2664 行。

注意点：

- 聚类只比较每个未访问 i 与后续 j 的相似度，不是完整图连通分量扩展；极端情形
  下可能漏掉 A-B、B-C 但 A-C 不相似的链式合并。
- `HF_ENDPOINT` 在函数内硬编码为 `https://hf-mirror.com`。

### 8.3 证据聚合和唯一边生成

看这些文件：

- 源码：`src/fusion/triples_aggregator.py`
- 输入：`data/interim/aligned_triples.jsonl`
- 输出：`data/processed/fused_triples.jsonl`

实现方法：

- 按 `(e1_name, e1_type, relation, e2_name, e2_type)` 分组。
- 每组聚合：
  - `pmid_set`
  - `engines_set`
  - `max_conf`
- 如果多个抽取引擎支持同一条边，每增加一个引擎 confidence 加 0.05，上限 1.0。
- 输出字段：
  - `entity_1`
  - `relation`
  - `entity_2`
  - `evidence.pmid_list`
  - `evidence.extraction_engines`
  - `computed_confidence`

当前效果：

- 2664 条 aligned triples 聚合成 652 条唯一边。
- Top 实体类型计数：
  - `Phenotype`: 590
  - `Drug`: 232
  - `Gene`: 96
  - `Disease`: 78
  - `Protein`: 75
- Top 关系：
  - `IMPROVES`: 54
  - `ASSOCIATED_WITH`: 39
  - `TREATS`: 24
  - `CAUSES`: 17
  - `CAUSED_BY`: 14
  - `REDUCES`: 14

## 9. 阶段 4: 图数据库、图计算和可视化

### 9.1 Neo4j 入库

看这些文件：

- 源码：`src/database/neo4j_importer.py`
- 输入：
  - `data/external/sma_gda_baseline.jsonl`
  - `data/processed/fused_triples.jsonl`
- 外部依赖：Neo4j 服务

实现方法：

- 使用 `neo4j.GraphDatabase.driver`。
- 创建唯一约束：

```cypher
CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE
```

- Open Targets baseline 入库：
  - `(:Entity:Disease {name: "Spinal Muscular Atrophy"})`
  - `(:Entity:Gene {name: gene_symbol})`
  - `(gene)-[:ASSOCIATED_WITH {score, source: "OpenTargets"}]->(disease)`
- 文献融合边入库：
  - `MERGE (e1:Entity {name})`
  - `SET e1:<entity type>`
  - `MERGE (e2:Entity {name})`
  - `SET e2:<entity type>`
  - `MERGE (e1)-[r:<relation>]->(e2)`
  - 边属性包含 `confidence`、`evidence_pmids`、`source = Literature_NLP`

注意点：

- 关系类型会做 upper、空格转下划线、连字符转下划线。
- 实体 label 和 relation type 仍通过字符串拼入 Cypher。虽然值参数化了，但 label
  和 relation type 需要额外 sanitization 才更稳。
- 没有 Neo4j 服务时，入库和 `topology_eval.py` 会失败。

### 9.2 离线图计算

看这些文件：

- 源码：`src/database/graph_analytics.py`
- 输入：
  - `data/processed/fused_triples.jsonl`
  - `data/external/sma_gda_baseline.jsonl`
- 输出：`data/processed/analytics_metrics.csv`

实现方法：

- 使用 NetworkX 构建 directed graph。
- 文献边权重使用 `computed_confidence`。
- Open Targets baseline 边权重使用 API `score`。
- 计算 PageRank。
- 转无向图后运行 `nx.community.louvain_communities`。
- 输出每个实体：
  - `Entity`
  - `Type`
  - `PageRank`
  - `Community_ID`

当前效果：

- 当前 metrics 有 844 个实体。
- PageRank 最高实体：
  - `Spinal Muscular Atrophy`: 0.105729
  - `motor function`: 0.007781
  - `reduced levels of the survival motor neuron (SMN) protein`: 0.007101
  - `SMA`: 0.006242
  - `Nusinersen`: 0.006005

注意点：

- 因为实体标准化仍不完全，`Spinal Muscular Atrophy`、`SMA`、
  `Spinal muscular atrophy (SMA)` 仍作为不同节点存在。

### 9.3 PyVis 可视化

看这些文件：

- 源码：`src/database/generate_pyvis.py`
- 输出：`docs/graph_viewer.html`
- 前端 vendor 依赖：
  - `lib/vis-9.1.2/`
  - `lib/tom-select/`
  - `lib/bindings/utils.js`

实现方法：

- 使用 `pyvis.network.Network`。
- 节点颜色：
  - Gene: red
  - Drug: green
  - Phenotype/Disease: blue
  - other: gray
- 节点大小由 PageRank 控制，约束在 12 到 65。
- 边 label 使用 relation。
- Open Targets baseline 边以灰色 `ASSOCIATED_WITH` 加入。

当前效果：

- 已生成 `docs/graph_viewer.html`，大小约 422 KB。

## 10. 阶段 5: 主题聚类

看这些文件：

- 源码：`notebooks/01_topic_clustering.py`
- Notebook：`notebooks/01_topic_clustering.ipynb`
- 输出：
  - `data/processed/clustered_abstracts.jsonl`
  - `notebooks/topic_barchart.html`

实现方法：

- 读取 `data/raw/pubmed_sma_abstracts.jsonl`。
- 丢弃空 abstract。
- 使用 `SentenceTransformer('NeuML/pubmedbert-base-embeddings')` 做 embedding。
- 使用 `BERTopic` 聚类。
- vectorizer 是 `CountVectorizer(stop_words="english")`。
- 输出每条摘要的 `topic` 到 clustered JSONL。
- 输出 topic bar chart HTML。

当前效果：

- clustered abstracts 有 1840 行，与 raw abstracts 行数一致。
- `topic_barchart.html` 大约 4.57 MB，是较大的可视化 HTML。

## 11. 阶段 6: 评估和新颖性发现

### 11.1 Baseline gene fuzzy evaluation

看这些文件：

- 源码：`src/evaluation/baseline_eval.py`
- 输入：
  - `data/external/sma_gda_baseline.jsonl`
  - `data/processed/extracted_triples.jsonl`

实现方法：

- 从 baseline 取 `gene_symbol` 集合。
- 从 extracted triples 中找 type 为 `Gene` 的实体。
- 使用 `thefuzz.fuzz.token_sort_ratio`，阈值 85。
- 分抽取引擎计算 precision、recall、F1。

### 11.2 Advanced relational baseline evaluation

看这些文件：

- 源码：`src/evaluation/baseline_eval_advanced.py`
- 历史输出：`artifacts/reports/final_reports.txt`

实现方法：

- baseline tuple 统一成 `(gene, sma)`。
- 只统计实体类型为 `Gene` 或 `Protein`，且另一端是 SMA 同义词的抽取结果。
- 用 exact normalized tuple match 计算 precision、recall、F1。

当前结果：

```text
Baseline tuples: 161

LLM_Qwen2.5_7B:
  extracted Gene-SMA tuples: 10
  precision: 0.1000
  recall: 0.0062
  F1: 0.0117

Regex_Fallback:
  extracted Gene-SMA tuples: 4
  precision: 0.5000
  recall: 0.0124
  F1: 0.0242
```

解释：

- 对 Open Targets gene-SMA baseline 的覆盖率非常低。
- 这不一定说明整个图谱无效，因为当前文献抽取更偏药物、表型、治疗效果和机制，
  而 baseline 只评估 gene-SMA 关系。

### 11.3 Human evaluation sample

看这些文件：

- 源码：`src/evaluation/human_eval_sampler.py`
- 输出：
  - `data/processed/human_evaluation_sample.csv`
  - `data/processed/human_evaluation_sample_scored.csv`

实现方法：

- 从 `fused_triples.jsonl` 固定随机种子 `42` 抽样 100 条。
- 输出字段：
  - `Entity_1`
  - `Relation`
  - `Entity_2`
  - `Evidence_PMIDs`
  - `Extracted_By`
  - `Human_Score`

当前人工评分效果：

- 有效打分行：101。
- `Human_Score == 2`: 37 行，严格支持率 36.63%。
- `Human_Score >= 1`: 78 行，宽松支持率 77.23%。
- 样本中 97 行来自 `LLM_Qwen2.5_7B`，3 行来自 `Regex_Fallback`，1 行来源为空。

### 11.4 LLM-as-a-judge evaluation

看这些文件：

- 源码：`src/evaluation/metrics_calculator.py`
- 输入：
  - `data/processed/human_evaluation_sample_scored.csv`
  - `data/raw/pubmed_sma_abstracts.jsonl`

实现方法：

- 用人工评分表中的 PMID 回查 raw abstracts。
- 拼接证据摘要，最多截断到 3000 字符。
- 调 SiliconFlow `Qwen/Qwen2.5-7B-Instruct` 作为生物学事实性评估器。
- 输出评分只能是：
  - `2`: abstract 完全支持三元组。
  - `1`: 部分支持或可推断。
  - `0`: 不支持。
- 最后计算 strict accuracy、lenient accuracy、average score 和 Cohen's Kappa。

注意点：

- 没有 `SILICONFLOW_API_KEY` 时，`get_llm_score()` 返回 fallback `1`，因此无 key
  情况下的结果不能当作真实 LLM judge。

### 11.5 Ablation study

看这些文件：

- 源码：`src/evaluation/ablation_study.py`
- 历史输出：`artifacts/reports/final_reports.txt`

实现方法：

- 用 NetworkX 分别加载：
  - pre-fusion: `data/processed/extracted_triples.jsonl`
  - post-fusion: `data/processed/fused_triples.jsonl`
- 比较：
  - total nodes
  - total edges
  - average node degree
  - isolated nodes ratio

当前结果：

```text
Pre-fusion:
  nodes: 720
  edges: 629
  average degree: 1.7472
  isolated nodes ratio: 59.31%

Post-fusion:
  nodes: 685
  edges: 618
  average degree: 1.8044
  isolated nodes ratio: 52.41%
```

解释：

- 融合后节点数下降，说明实体合并起作用。
- 平均度上升，孤立比例下降，说明图连通性改善。

### 11.6 Novelty discovery

看这些文件：

- 源码：`src/evaluation/novelty_analysis.py`
- 输出：`data/processed/llm_novel_discoveries.csv`

实现方法：

- baseline genes 来自 Open Targets。
- 只看 `extracted_by` 包含 `LLM` 的抽取结果。
- 找 Gene/Protein 与 SMA 同义词相关、但 gene 不在 baseline genes 中的候选。
- 聚合 PMID、平均 confidence、mention count。

当前效果：

- 共解析 2664 条 extracted triples。
- 当前新颖候选 CSV 有 10 条数据行。
- 候选包括 `AAV9`、`FECH`、`SMN-targeted interventions`、`NAIP exon 5`、
  `leptin protein` 等。

注意点：

- 报告里称这些是 "novel False Positive relationships"，措辞不准确。更准确说法
  应该是 "baseline-missing candidate relationships"。它们需要人工复核，不应直接
  当成真正科学发现。

### 11.7 Neo4j topology evaluation

看这些文件：

- 源码：`src/evaluation/topology_eval.py`
- 历史输出：`artifacts/reports/topo_out.txt`

实现方法：

- 连接 Neo4j 后查询：
  - total nodes
  - isolated nodes
  - total relationships
  - average degree
  - isolated ratio

注意点：

- 历史输出显示曾出现无法连接 `localhost:7687` 的情况。运行前必须确认 Neo4j 服务
  和密码配置。

## 12. 历史报告和归档产物

归档目录：

- `artifacts/reports/`
- `artifacts/test-results/`

其中：

- `artifacts/reports/final_reports.txt`: advanced baseline、ablation、novelty
  discovery 的组合结果。
- `artifacts/reports/output_combined.txt`: 与 final reports 类似的组合输出。
- `artifacts/reports/topo_out.txt`: Neo4j topology 查询失败或结果输出。
- `artifacts/reports/metrics_out.txt`: LLM/human evaluation 相关输出。
- `artifacts/test-results/ot_test_result.json`: Open Targets GraphQL 测试响应。

## 13. 如果要了解某个阶段，应该先看什么

| 目标 | 先看源码 | 再看产物 | 备注 |
| --- | --- | --- | --- |
| Open Targets baseline | `src/crawler/api_fetcher.py` | `data/external/sma_gda_baseline.jsonl` | `tests/smoke/test_opentargets_api.py` 是小测试 |
| PubMed 抓取 | `src/crawler/pubmed_crawler.py` | `data/raw/pubmed_sma_abstracts.jsonl` | 注意 Entrez email |
| LLM 三元组抽取 | `src/extraction/llm_extractor.py` | `data/processed/llm_extracted_triples.jsonl` | 需要 SiliconFlow key |
| 本地兜底抽取 | `src/extraction/local_pipeline.py` | `data/processed/spacy_extracted_triples.jsonl` | 实际主要是 regex |
| 抽取结果合并 | `src/extraction/merge_triples.py` | `data/processed/extracted_triples.jsonl` | 按 PMID+三元组签名去重 |
| 实体词典标准化 | `src/fusion/dictionary_mapper.py` | `data/interim/mapped_triples.jsonl` | 内置小词典 |
| 语义对齐 | `src/fusion/semantic_aligner.py` | `data/interim/aligned_triples.jsonl` | `all-MiniLM-L6-v2` |
| 融合唯一边 | `src/fusion/triples_aggregator.py` | `data/processed/fused_triples.jsonl` | 652 条当前唯一边 |
| Neo4j 入库 | `src/database/neo4j_importer.py` | Neo4j 数据库 | 需服务可连接 |
| 离线图指标 | `src/database/graph_analytics.py` | `data/processed/analytics_metrics.csv` | PageRank + Louvain |
| 图可视化 | `src/database/generate_pyvis.py` | `docs/graph_viewer.html` | PyVis HTML |
| 主题聚类 | `notebooks/01_topic_clustering.py` | `data/processed/clustered_abstracts.jsonl` | BERTopic |
| baseline 评估 | `src/evaluation/baseline_eval*.py` | `artifacts/reports/final_reports.txt` | gene-SMA 覆盖很低 |
| 人工评估 | `src/evaluation/human_eval_sampler.py` | `human_evaluation_sample*_scored.csv` | 人工分数已有 |
| LLM judge | `src/evaluation/metrics_calculator.py` | 控制台输出 | 无 key 时 fallback 不可信 |
| 消融实验 | `src/evaluation/ablation_study.py` | `artifacts/reports/final_reports.txt` | 融合改善连通性 |
| 新颖性候选 | `src/evaluation/novelty_analysis.py` | `data/processed/llm_novel_discoveries.csv` | 需人工复核 |

## 14. 推荐的端到端运行顺序

从仓库根目录运行：

```powershell
conda activate KG_SMA_env

python src/crawler/api_fetcher.py
python src/crawler/pubmed_crawler.py

python src/extraction/llm_extractor.py
python src/extraction/local_pipeline.py
python src/extraction/merge_triples.py

python src/fusion/dictionary_mapper.py
python src/fusion/semantic_aligner.py
python src/fusion/triples_aggregator.py

python src/database/graph_analytics.py
python src/database/generate_pyvis.py

python src/evaluation/baseline_eval_advanced.py
python src/evaluation/ablation_study.py
python src/evaluation/novelty_analysis.py
```

可选，需要外部服务：

```powershell
python src/database/neo4j_importer.py
python src/evaluation/topology_eval.py
python src/evaluation/metrics_calculator.py
```

注意：

- `llm_extractor.py` 和 `metrics_calculator.py` 需要 `SILICONFLOW_API_KEY`。
- `neo4j_importer.py` 和 `topology_eval.py` 需要 Neo4j。
- `semantic_aligner.py` 和 topic clustering 需要 HuggingFace 模型可下载或已有缓存。

## 15. 当前实现质量和已知问题

已经完成的能力：

- 能抓取 Open Targets baseline。
- 能抓取 PubMed SMA 摘要。
- 能用 LLM 和规则方法生成三元组。
- 能把抽取结果标准化、语义对齐并融合为唯一图谱边。
- 能离线计算 PageRank 和社区。
- 能生成 PyVis HTML 图谱。
- 能进行 baseline 对比、人工评分样本、消融实验和新颖性候选生成。

主要效果：

- 图谱融合后从 2664 条抽取三元组收敛到 652 条唯一边。
- 融合后节点数从 720 降到 685，平均度从 1.7472 升到 1.8044，孤立比例从
  59.31% 降到 52.41%。
- 人工评分样本宽松支持率 77.23%，严格支持率 36.63%。
- baseline gene-SMA exact relational recall 很低，最高 0.0124。

已知问题：

- `requirements.txt` 之前缺少实际源码依赖，已补充。
- 抽取 schema 未严格收敛，LLM 产物中出现 prompt 未声明的实体类型。
- `local_pipeline.py` 文件名和产物名含 `spacy`，但核心实现是规则兜底。
- disease/SMA 标准化仍不完全，图中还有 `SMA`、`Spinal Muscular Atrophy`、
  `Spinal muscular atrophy (SMA)` 等重复概念。
- Neo4j 动态 label/relation type 需要更严格 sanitization。
- `novelty_analysis.py` 把候选称为 "False Positive relationships"，容易误导。
- 历史报告中有旧路径 `D:\kg_sma_0323`，当前仓库路径是 `D:\kg_sma_0420`。
- `tests/smoke/test_opentargets_api.py` has been moved out of the root and now
  writes to `artifacts/test-results/`.

## 16. 下一步建议

1. 固化一个 `scripts/run_pipeline.ps1`，按阶段顺序运行并把日志写入
   `artifacts/reports/`。
2. 把三元组 schema 做成验证器，约束 entity type、relation type 和必填字段。
3. 扩展 `dictionary_mapper.py`，重点合并 SMA disease/phenotype 同义表达。
4. 把 `local_pipeline.py` 重命名或重构为真正的 local NLP extractor。
5. 给 Neo4j importer 增加 label/relation whitelist 或 sanitizer。
6. 把 `novelty_analysis.py` 输出术语改为 candidate discoveries，并增加人工复核状态列。
7. 给每个阶段加小样本测试，避免全量 API/LLM 调用才能验证。
