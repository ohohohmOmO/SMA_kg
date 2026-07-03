# Source Code

生产代码按流水线 Stage 和跨阶段功能组织。`src` 保持为稳定 Python 包，
避免为了目录外观破坏现有导入接口。

| 流程 | 目录 | 职责 |
| --- | --- | --- |
| Stage 1 | `crawler/` | Open Targets、PubMed、BERTopic 和主题平衡检索 |
| Stage 2 | `extraction/` | LLM 抽取、规则候选、证据对齐与 promotion gate |
| Stage 3 | `fusion/` | 词典映射、语义融合、边聚合与关系冲突 |
| Stage 4 | `database/` | Neo4j 导入、图分析和 PyVis 输出 |
| Shared | `biomedical/` | schema、confidence 和 Evidence Span Alignment |
| Graph RAG | `evidence/`, `qa/` | Evidence Context、检索、邻域扩展和答案校验 |
| Evaluation | `evaluation/` | 抽取、拓扑、消融和新颖性评估 |

从仓库根目录运行脚本。正式命令以
`docs/start-here/PROJECT_OVERVIEW.md` 为准。
