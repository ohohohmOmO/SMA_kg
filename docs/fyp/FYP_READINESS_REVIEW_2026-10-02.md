# 毕设完成度复核与剩余改进

日期：2026-10-02。对象：当前 SMA 项目和学校 FYP 要求。

## 结论

400 条人工标记来源问题已经解决。项目目前有可演示、可追溯、可复现、
可量化评价的核心原型；仍存在重要的实体融合问题，不能只剩报告排版，
也不能把原始四项创新方案全部标记为完成。评分表没有给定一个最低抽取
准确率或规定必须完成 GraphRAG，不能仅从当前百分比判断课程成绩。

本次确认原文：“这400条均为人工标记，最后给到ChatGPT完成表格的而已”。
据此按人工标记报告，不再以表格中的 ChatGPT 名称认定标签为模型判断。
原表、原始元数据和此前运行保持不变；没有补造标记者身份、独立复审或裁决。

最新结果：`artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/`。
其中 `completion_audit.json` 保存本次实际核查；此前未确认版本是历史快照。

## 逐项验收

| 项目 | 状态 | 依据与边界 |
| --- | --- | --- |
| 数据获取、抽取、schema、聚合与来源保持 | 已有实现与复现材料 | 4,554 摘要、18,288 抽取记录；结构/来源检查通过。工程检查不等于事实正确。 |
| 可视化与证据链 | 核心已实现并做功能检查 | 完整文献图、局部邻域、类型/关系筛选、原始实体与摘要、多个 PMID、潜在冲突、外部标识。10 项检查是开发过程执行的功能验收，不是独立用户研究。 |
| 400 条人工标记及抽取评价 | 已完成来源确认和统计 | 随机主集 300；挑战集 100 单列；严格/部分/不支持及区间均可报告。没有独立第二评审、细分字段准确率或抽取 Recall/F1。 |
| 融合结构对照 | 已完成 | 同一输入、同一聚合，13,697→13,080→11,155；证据计数保持。 |
| 融合身份正确性 | 未完成且已发现问题 | 固定 30 项尚无判断；出现 SMN2→SMN1、SMA 亚型变化；类型映射键存在可复现缺陷。 |
| 一项证据改进及评价 | 已完成本次定义的定位/分流目标 | 原文偏移、排版归一、顺序片段、保守送审；不是自动声明语义验证。 |
| Neo4j 当前验收 | 未完成 | 本次仅尝试只读连接，返回 ServiceUnavailable，未执行修改；历史导入成功不能替代当前运行验证。名称身份模型与类型化视图也不一致。 |
| 结果与讨论 | 已有章节草稿 | 人工标记口径已更新，图表与数字可复现；仍需完整方法、文献讨论、目标回顾和最终报告。 |
| 原始四项创新方案 | 未全部完成 | GraphRAG、引用检查和声明验证没有实现/评价。首轮 DOCX 仍承诺这些模块，须与实际核心范围统一。 |
| 正式提交材料与持续表现 | 尚不能确认完成 | 真正的 logbook、导师讨论、身份/签字、海报口试和正式提交须来自实际活动，程序产物不能代替。 |

## 必须优先处理的技术问题

### 1. 修正实体身份与类型约束，再评价融合

映射快照中，Gene SMN2→SMN1 发生 982 次端点转换，涉及 618 个 PMID。
这是转换次数，不是 982 条独立融合边错误率。NCBI 分别登记
[SMN1（Gene ID 6606）](https://www.ncbi.nlm.nih.gov/gene/6606/) 和
[SMN2（Gene ID 6607）](https://www.ncbi.nlm.nih.gov/gene/6607)，不能仅因名称/
embedding 相近就把这两个 Gene 标识当成同义词。Disease SMA type III→type 2
发生 11 次、7 个 PMID；type 3→type 2 发生 31 次、16 个 PMID。其他类型的
亚型转换在 JSON 中单列，不能把各组 PMID 数简单相加。

`semantic_aligner.py` 虽按类型计算 embedding，却以名称单独索引
`global_alignment_map`。本次抽取实际键和查询表达式作合成复现，Gene 的
Shared 名称被 Protein 映射覆盖。输入有 195 个跨类型同名名称。另一个
合成例说明：A-B/B-C 相似度 .89 的连通分量可将 A-C=.60 合在一起；
阈值 .88 不意味着每个成员都与最终规范名达到 .88。这是单链接设计的风险，
不能靠提高阈值就宣布解决。

下一步验收：typed keys/frequency；保留权威基因标识、亚型/变异限定；
在新输出中验证规则，复跑融合对照；对固定映射条件完成 30 项判断并报告
错误、无法判断与区间。改规则后不得拿旧条件的标签直接冒充新条件结果。
本次是检查，没有运行新对齐模型或覆盖 canonical 数据。

### 2. 抽取质量仍需解释与有针对性的改善

主随机集 79/300 严格支持（26.3%），141/300 部分支持（47.0%），
80/300 不支持（26.7%）。73.3% 是“严格＋部分”的宽松口径，不能当作
完全正确率。常见人工错误说明为条件/强度丢失、类型错误和证据问题。
不能靠删除这 400 条中的错误案例再在同一集合宣布泛化提升。

若进一步改抽取，应优先保留实验对象、条件、否定与关系强度，改进类型
规则/提示和证据完整性；固定开发/测试边界，用未参与调参的材料评价。
这是基于现有错误的下一轮优化，不要求为本次检查重新全量调用 LLM。

### 3. 保持证据筛查的真实作用，并验证数据库身份

主内部测试 n=202：保留片段合格率 51.0%→81.4%，保留率 29.2%，
合格片段检出率 46.6%，保留关系的严格支持率 40.7%。改进是优先分流，
大量合格片段也被送审。当前可以报告这一改进与代价，但不能写成
81.4% 图谱准确率或已实现语义验证，也不应据此自动删边。

数据库代码按 Entity.name 唯一合并；快照文献有 6,684 个（名称,类型）
节点，却只有 6,524 个名称。须明确多类型节点与不同实体的身份政策，
然后做可逆迁移/来源保持和当前只读计数核对，不能为了计数直接清库。
离线展示仍可使用，不依赖本次未连接的 Neo4j。

## 报告目标应怎样改

首轮 `05_GCU_Specification_and_Preliminary_Report_Draft.docx` 的
Measurable Outcomes、Task 7、Innovation 2–4、RQ3/RQ4 和 Work Plan
仍包含 GraphRAG/引用/声明验证。已交付的是本次核心三问，需要统一这些
位置的表述；原草稿尚未在本次检查中被修改，也未虚构导师同意记录。

如果采用用户当前的核心范围，可使用以下英文替换文字：

> The core project will deliver a reproducible SMA knowledge-graph construction
> and source-inspection system. It will evaluate extraction support using 300
> randomly sampled human-labelled predictions and a separate 100-item challenge
> set, compare raw, dictionary and semantic normalization under identical
> aggregation, and implement and evaluate source-span traceability and review
> triage. GraphRAG, answer-citation checks and claim-level entailment are optional
> extensions rather than completed core outcomes.

- RQ1: How well are the extracted SMA relations supported by their source abstracts?
- RQ2: How do dictionary and semantic normalization affect graph compression,
  provenance preservation and erroneous entity merges?
- RQ3: How does source-span traceability and conservative triage change evidence
  adequacy, candidate retention and review workload?

若实际已批准范围仍要求四项创新全部完成，则后三项仍是待开发任务，不能
仅通过把它们改称 future work 宣告完成。此次用户五步顺序的核心工作和
原草稿的完整四项方案必须分别说明。

## 与评分表的关系

学校 Final Report 占 50%，其中 Technical Content & Quality of Analysis
权重为 3，其余四类各为 1。持续表现的 Technical Quality 权重为 2，
其余三类各为 1。已有代码、界面和计数是基础；为增强成绩依据，应说明
上述错误为何产生、如何处理、怎样评价，以及改进的代价。评分表没有
指定 400/80/30 条为学校强制数量，也没有据现有支持率自动判定等级的规则。

来源（本次读取原评分表完整相关页；以下清单为复核依据）：

- `C:\Users\jon15\Desktop\大四上\FYP\04_最终提交_2027-04-28_internal\02_模板与要求\Final Report Marking Schema (50%).pdf`
- `C:\Users\jon15\Desktop\大四上\FYP\00_总览_要求与时间线\Student Performance Marking Schema (10%).pdf`
- 首轮报告 DOCX 的目标/研究问题/工作计划；`FYP_COMPLETION_PLAN_2026-10-02.md`。
- 最新运行 JSON、`completion_audit.json`、当前 aligner/importer 源码。

## 建议推进顺序

先修实体身份和类型映射 → 冻结改进后的融合条件并完成 30 项映射审核 →
复跑结构/来源对照和当前数据库只读验收 → 分析人工错误与证据质量/覆盖
代价 → 统一目标并整合完整报告与演示材料。

不再要求确认或重填 400 条。独立第二评审是增强标注可信度、支持一致性
结论的可选方法，不能为了填 kappa 捏造；当前缺失应如实写明。
