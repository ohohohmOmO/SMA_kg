# Pipeline Data

这里保存可被流水线继续消费的数据，不保存一次性日志或运行报告。

| 目录 | 含义 |
| --- | --- |
| `raw/` | Stage 1 原始 PubMed 输入 |
| `external/` | Open Targets 等外部基线数据 |
| `interim/` | Stage 2–3 可审查的中间结果 |
| `processed/` | 已验证并供后续阶段消费的 canonical 输出 |

按 Stage 的输入、输出和 promotion 规则见
`docs/start-here/PROJECT_OVERVIEW.md`。每次运行的快照、manifest 和日志放在
`results/runs/`，不要混入本目录。
