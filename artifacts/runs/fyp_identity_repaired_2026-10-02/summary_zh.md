# 四项修复结果

实体：已恢复982次SMN2错并，保留18288条证据，当前13001条文献边、9053个类型化节点。

抽取：原主集严格支持26.3%，部分支持47.0%，宽松73.3%不等于完全正确率。新增条件/类型/完整证据筛查，以下为原始候选上的回顾性内部测试。

| Screen | Retained/n | Strict supported retained/total | Strict PPV | Strict false accepts | Strict positives routed to review | Original adequate-span PPV |
| --- | --- | --- | --- | --- | --- | --- |
| all_predictions | 202/202 | 55/55 | 27.2% | 147 | 0 | 51.0% |
| previous_evidence_triage | 59/202 | 24/55 | 40.7% | 35 | 31 | 81.4% |
| context_type_screen | 17/202 | 6/55 | 35.3% | 11 | 49 | 76.5% |
| model_direct_screen | 89/202 | 32/55 | 36.0% | 57 | 23 | 59.6% |
| combined_screen | 30/202 | 14/55 | 46.7% | 16 | 41 | 86.7% |

数据库：passed；详见database_acceptance.json。

英文结果与讨论：results_and_discussion.md。可视化：graph_explorer.html、evidence_explorer.html。30项新融合审核为可选补充质量证据，不能伪造已完成；原400项不用重新标注。
