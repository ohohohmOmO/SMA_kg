# SMA Knowledge Graph

本仓库用于构建脊髓性肌萎缩症（SMA）生物医学知识图谱，并提供
Graph RAG、证据校验、关系冲突分析与 Neo4j 图分析能力。

## 从这里开始

所有需要在开始工作或恢复上下文时阅读的资料，统一放在
[`docs/start-here/`](docs/start-here/README.md)。

- 项目全貌：[`docs/start-here/PROJECT_OVERVIEW.md`](docs/start-here/PROJECT_OVERVIEW.md)
- 当前计划：[`docs/start-here/PLAN.md`](docs/start-here/PLAN.md)
- 领域词汇：[`docs/start-here/CONTEXT.md`](docs/start-here/CONTEXT.md)
- 最新交接：[`docs/start-here/PROJECT_HANDOFF_2026-06-09.md`](docs/start-here/PROJECT_HANDOFF_2026-06-09.md)

## 顶层目录

```text
src/          按 Stage 和功能组织的生产代码
tests/        单元测试与外部服务 smoke tests
notebooks/    探索性分析和可视化实验
resources/    生物医学 schema 与实体词典
data/         流水线输入、中间数据和 canonical 数据
results/      运行记录、报告、测试输出和可视化成品
docs/         必读资料、设计文档、复现记录和历史归档
```

环境变量保存在本地 `.env`；真实密钥不得提交。运行命令与当前状态请以
[`docs/start-here/PROJECT_OVERVIEW.md`](docs/start-here/PROJECT_OVERVIEW.md)
和 [`docs/start-here/PLAN.md`](docs/start-here/PLAN.md) 为准。
