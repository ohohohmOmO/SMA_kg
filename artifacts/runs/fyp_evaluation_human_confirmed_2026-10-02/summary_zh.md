# SMA 毕设评价结果与交付状态

运行：`fyp_evaluation_human_confirmed_2026-10-02`。日期：2026-10-02。

## 标签口径

用户已确认400条均为人工标记，ChatGPT仅整理表格。原工作簿元数据保留，不再将其中的ChatGPT名称解释为人工标记者身份。
独立第二评审为空，不能报告人际一致性或把多轮AI自查称为独立人工复核。
中文合格/不合格已规范化；原始表及空白细分字段未修改。

## 抽取评价

| Sample | n | Direct (2) | Partial (1) | Unsupported (0) | Strict | Lenient | Adequate spans |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random main | 300 | 79 | 141 | 80 | 26.3% | 73.3% | 151 |
| Challenge | 100 | 5 | 50 | 45 | 5.0% | 55.0% | 39 |

严格支持与部分支持分开。Recall/F1、独立实体类型/方向准确率不可从现有材料计算。

## 融合对照

| Condition | Input records | Typed nodes | Unique relation edges | Weak components | Potential conflicts | Self-loop edges |
| --- | --- | --- | --- | --- | --- | --- |
| raw | 18288 | 9256 | 13697 | 334 | 32 | 0 |
| dictionary | 18288 | 9225 | 13080 | 333 | 35 | 2 |
| semantic | 18288 | 6684 | 11155 | 171 | 59 | 13 |

18,288条证据计数均保留，来源集合一致，语义条件复现canonical字节一致。
节点按名称＋类型计数，与Neo4j按名称合并的历史口径不同。压缩不等于正确融合。
30个变更映射单元已固定随机抽样并附原文，尚无人工判断。

## 证据验证

| Gate | Retained / n | Span PPV | Adequate-span sensitivity | Specificity | Strict relation support among retained |
| --- | --- | --- | --- | --- | --- |
| nonempty | 202 / 202 | 51.0% | 100.0% | 0.0% | 27.2% |
| literal | 181 / 202 | 49.7% | 87.4% | 8.1% | 26.5% |
| traceable | 194 / 202 | 50.0% | 94.2% | 2.0% | 26.3% |
| triage_gate | 59 / 202 | 81.4% | 46.6% | 88.9% | 40.7% |

测试主集 n=202，按PMID与开发集分开。规则为回顾性内部评价。
保守筛查提高保留片段的参考合格比例，但大量合格记录也被送审。
它是待审分流，不是自动语义验证或删边依据；81.4%不是图谱准确率。

## 交付与下一步

- 英文结果与讨论草稿：`results_and_discussion.md`。
- 评价候选与融合审核界面：`evidence_explorer.html`。
- 完整图谱、局部有向关系和融合边来源：`graph_explorer.html`。
- 操作手册与实际验收记录：`USAGE_AND_ACCEPTANCE_zh.md`。
- 三张科学图：`figures/`，提供PNG与SVG。
- 融合30项：界面中选择同一实体/不同实体/无法判断，导出JSON。
- 审核导入：`python src/evaluation/summarize_fusion_review.py --queue <run>/fusion_review_30.jsonl --reviews <export.json> --output <new_report.json>`。
- 400条人工标记来源已由用户确认，不需要重审或重填；融合正确性仍需这30项新判断。

所有未取得的标签指标保持缺失，不用自动分数代替。本文不能代替完整学校最终报告；
目标、方法、文献综述、风险/伦理、真实日志、口试材料仍按课程要求整合。
