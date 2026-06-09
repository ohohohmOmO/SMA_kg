# 华为 AI 应用工程师方向 Feature Roadmap

本文档基于当前 SMA 知识图谱项目，总结若干后续开发 feature，使项目更贴合
“AI 应用工程师 / AI 技术应用”类岗位要求，重点突出大模型应用开发、知识图谱、
向量检索、NLP、模型评估、图算法和工程化能力。

## 岗位要求与当前项目基础

当前主线项目已经具备以下基础：

- 使用 Python 构建完整 AI 数据流水线，覆盖 PubMed/Open Targets 数据采集、
  LLM 关系抽取、语义融合、Neo4j 导入、图分析、可视化和评估。
- 使用 SiliconFlow 调用 `deepseek-ai/DeepSeek-V4-Flash` 完成全量文献三元组抽取。
- 使用 biomedical schema 做实体类型、关系类型、关系极性和冲突规则约束。
- 使用 BERTopic、sentence-transformers、PubMedBERT embedding 做主题聚类和实体语义对齐。
- 使用 Neo4j、NetworkX、PyVis 构建和展示 SMA 生物医学知识图谱。

后续 feature 应优先把这些能力包装成更明显的“大模型应用 + 知识图谱 + 工程化”
成果，而不仅仅是离线数据处理脚本。

## Feature 1：SMA Graph RAG 智能问答系统

目标：基于 SMA 知识图谱构建智能问答应用，让用户可以用自然语言询问 SMA 相关
基因、药物、表型和证据文献。

核心能力：

- 将 PubMed 摘要、LLM 抽取三元组、融合图谱边、Open Targets 记录构建为向量索引。
- 实现混合检索：向量相似度检索 + Neo4j 图邻域检索。
- 调用大模型生成带 PMID 引文和图路径证据的回答。
- 返回自然语言答案、证据三元组、PMID、置信度和相关实体路径。

技术关键词：

- RAG、Graph RAG、向量数据库、Embedding、Neo4j、LLM Prompt、知识图谱问答、
  NLP、DeepSeek/Qwen/GPT 类模型应用。

建议落地：

- 新增 `src/qa/`，包含 retriever、graph context builder、prompt builder 和 CLI/FastAPI 入口。
- 支持本地向量库，例如 FAISS 或 Chroma。
- 增加固定样例问题测试，例如 “Nusinersen 对 motor function 有什么证据？”。

简历表达：

> 基于 SMA 生物医学知识图谱实现 Graph RAG 智能问答系统，结合向量检索、
> Neo4j 图遍历和大模型生成，实现带 PMID 证据引用的医学问答。

## Feature 2：金标准评审与微调数据集构建

目标：把当前 `build_gold_candidates.py` 扩展为完整的人工评审和微调数据准备流程，
为后续 BioBERT、UIE-med 或其他关系抽取模型微调提供数据基础。

核心能力：

- 从当前 `18288` 条 LLM-only canonical triples 中分层抽样 500-1000 条候选。
- 输出 review-ready CSV/HTML，支持标注 supported、partially_supported、
  unsupported、wrong_entity、wrong_relation、missing_evidence 等标签。
- 统计不同关系类型、实体类型、置信度区间的准确率。
- 导出监督微调 JSONL，为医学关系抽取模型训练做准备。

技术关键词：

- 数据标注、模型评估、NLP 关系抽取、微调数据构建、BioBERT、UIE-med、
  supervised fine-tuning、precision/recall/error analysis。

建议落地：

- 扩展 `src/extraction/build_gold_candidates.py`。
- 新增 `src/evaluation/gold_review_metrics.py`。
- 输出到 `artifacts/runs/stage2_gold_candidates_<timestamp>/`，保留 manifest 和统计摘要。

简历表达：

> 设计医学关系抽取金标准评审流程，构建可用于 BioBERT/UIE-med 微调的数据集，
> 并基于人工标签评估 LLM 抽取质量和错误类型。

## Feature 3：LLM 关系冲突自动裁决

目标：针对当前 `data/interim/relation_conflicts.jsonl` 中的 59 个关系冲突，构建
LLM 辅助裁决流程，提升知识图谱质量。

核心能力：

- 汇总冲突实体对的所有关系、PMID 和 evidence span。
- 调用大模型判断冲突是真实语境差异、方向错误、抽取错误，还是关系归一化问题。
- 输出裁决结果：保留关系、驳回关系、理由、置信度、证据 PMID。
- 将裁决状态回写为 `accepted`、`needs_review` 或 `rejected_candidate`。

技术关键词：

- LLM verifier、prompt engineering、evidence-grounded reasoning、知识图谱冲突检测、
  biomedical relation normalization、人机协同评审。

建议落地：

- 新增 `src/fusion/adjudicate_relation_conflicts.py`。
- 支持 `--dry-run`，无 API key 时也能生成待裁决 payload。
- 输出 `data/interim/relation_conflict_adjudications.jsonl`。

简历表达：

> 构建 LLM 辅助的知识图谱关系冲突裁决模块，基于文献证据自动分析正负极性冲突，
> 提升医学知识图谱融合质量。

## Feature 4：知识图谱链路预测与新发现排序

目标：在当前 SMA 图谱基础上增加图算法/图机器学习 feature，预测潜在的
基因-疾病、药物-表型、蛋白-机制等候选关系。

核心能力：

- 基于 fused triples 和 Open Targets 构建图机器学习数据集。
- 使用 Node2Vec、GraphSAGE 或 GNN-ready export 生成节点表示。
- 对候选边进行打分，并与已知 Open Targets 关系做对比。
- 输出 novel discovery ranking，包含候选关系、图邻域、PageRank、证据文献和置信度。

技术关键词：

- 知识图谱、图神经网络、GNN、Node2Vec、Link Prediction、Graph Embedding、
  Novel Discovery、NetworkX、Neo4j。

建议落地：

- 新增 `src/evaluation/link_prediction.py`。
- 第一版先做确定性的 Node2Vec/图嵌入 baseline，再预留 GNN 接口。
- 输出 `data/processed/kg_link_prediction_candidates.csv`。

简历表达：

> 基于 SMA 知识图谱实现链路预测与新关系发现排序，使用图嵌入算法挖掘潜在
> 基因、药物和表型关联。

## Feature 5：可复现 AI Pipeline 编排器

目标：把 Stage 1-4 的多个 runner 封装成统一的 pipeline orchestration CLI，
体现 AI 应用工程中的可复现、可恢复、可观测能力。

核心能力：

- 一条命令选择性执行 Stage 1-4。
- 自动检查 `SILICONFLOW_API_KEY`、Neo4j 连接、`HF_ENDPOINT`、输入 hash 和输出路径。
- 支持 `--dry-run`、`--from-stage`、`--to-stage`、`--promote`、`--write-handoff`。
- 每次运行生成 manifest、validation summary、日志和 handoff 文档。
- validation 失败时拒绝 promote canonical output。

技术关键词：

- AI 工程化、pipeline orchestration、MLOps、workflow automation、artifact
  tracking、reproducibility、validation gate、resume/retry。

建议落地：

- 新增 `src/pipeline/run_pipeline.py`。
- 复用现有 `run_stage2_extraction.py`、`run_stage3_fusion.py` 和
  `run_stage4_graph.py`，避免重复实现。

简历表达：

> 设计并实现可复现 AI 知识图谱流水线编排器，支持阶段化执行、环境预检、
> 断点恢复、产物校验和自动 handoff 报告生成。

## Feature 6：交互式图谱探索与证据审查 UI

目标：把当前 `docs/graph_viewer.html` 从“全图展示产物”升级为可交互的图谱审查工具。

核心能力：

- 支持按实体类型、关系类型、置信度、PageRank、review status 过滤。
- 支持实体搜索，例如 `SMN1`、`SMN2`、`Nusinersen`、`motor function`。
- 点击边时展示 evidence PMIDs、evidence_count、extraction_engines 和冲突状态。
- 高亮 `needs_review` 冲突边，辅助人工审查。

技术关键词：

- 知识图谱可视化、AI 产品化、人机协同评审、前端交互、图数据探索、
  evidence inspection。

建议落地：

- 轻量方案：扩展 `src/database/generate_pyvis.py`，继续生成离线 HTML。
- 完整方案：新增 `src/ui/graph_inspector/`，做本地 Web UI。

简历表达：

> 开发交互式医学知识图谱探索工具，支持关系过滤、实体搜索、证据查看和冲突边审查，
> 提升图谱质检和业务展示效率。

## 推荐优先级

1. SMA Graph RAG 智能问答系统。
2. LLM 关系冲突自动裁决。
3. 金标准评审与微调数据集构建。
4. 交互式图谱探索与证据审查 UI。
5. 知识图谱链路预测与新发现排序。
6. 可复现 AI Pipeline 编排器。

优先做 Graph RAG 和冲突裁决，最容易体现“大模型应用开发 + 知识图谱 + NLP”的
岗位匹配度；再做金标准和图算法，可以进一步体现模型评估、微调准备和 AI 算法能力；
最后补齐 UI 和 pipeline 编排，增强工程化与产品化表达。
