# 当前交付使用和验收

离线打开 `graph_explorer.html`（同内容已成为 `docs/graph_viewer.html`）或 `evidence_explorer.html`。
搜索SMN2，选Gene及文献节点，再选TARGETS和Nusinersen→SMN2，可查看37个不同PMID的原始记录、摘要、高亮和条件提示。Gene/Protein、文献/外部来源分别保留。模型/启发式筛查标记都不是人工事实确认。

400条人工标签可搜索，原标签和原始片段保持不变，新增完整原句、规则理由及模型回复另列。结果总览同时显示严格支持、保留量、误保留和送审量。30项融合判断为空，未虚构评审；若不主张映射正确率，可以继续写作而不填写。

实际浏览器验收见 `ui_acceptance.json` 与 `graph_ui_acceptance.png`；17项跨文件验收及当前代码哈希见 `final_verification.json`。在线数据库完整验收 `database_acceptance.json`，额外只读核查 `completion_audit.json`。这些证明工程一致性，不能证明所有生物医学关系正确或独立用户可用性。

本次结果、复现和下一步见 `docs/fyp/FYP_FOUR_REPAIRS_STATUS_2026-10-02.md`；完整使用当前Neo4j版本的查询见 `docs/reproduction/FYP_FOUR_REPAIRS_2026-10-02.md`。历史Entity图保留，查询必须限定活动版本。学生真实日志、导师资料和签名仍需本人完成；没有捏造学术活动。
