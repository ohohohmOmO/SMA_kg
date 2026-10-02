"""Generate offline explorer, scientific figures and evidence-based report drafts."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.evaluation.audit_fyp_inputs import load_jsonl
from src.evaluation.fyp_dataset import sha256


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def percent(value):
    return "not available" if value is None else f"{100 * value:.1f}%"


def markdown_table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] +
                     ["| " + " | ".join(str(x) for x in row) + " |" for row in rows])


def figures(out, review, fusion, evidence):
    target = out / "figures"
    target.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 180})
    def save(fig, name):
        fig.savefig(target / (name + ".png"), bbox_inches="tight")
        fig.savefig(target / (name + ".svg"), bbox_inches="tight")
        svg = target / (name + ".svg")
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = ["Random main (n=300)", "Challenge (n=100)"]
    left = [0, 0]
    for label, title, color in (("2", "Direct support", "#176b59"), ("1", "Partial support", "#d2a54d"), ("0", "Unsupported", "#b76463")):
        values = [review["reference_statistics"][g]["labels"][label] for g in ("primary_random", "challenge")]
        ax.barh(names, values, left=left, label=title, color=color)
        for i, value in enumerate(values):
            if value > 10:
                ax.text(left[i] + value / 2, i, str(value), ha="center", va="center", color="white")
        left = [a + b for a, b in zip(left, values)]
    ax.set_xlabel("Predicted triples (reference labels)"); ax.set_xlim(0, 315)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
    ax.set_title("Source support: random and challenge samples remain separate")
    fig.tight_layout(); save(fig, "reference_support")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    conditions = ["raw", "dictionary", "semantic"]
    for ax, key, title in zip(axes, ("typed_nodes", "unique_relation_edges"), ("Typed nodes", "Relation-specific edges")):
        values = [fusion["conditions"][c][key] for c in conditions]
        ax.bar(["Raw", "Dictionary", "+ Semantic"], values, color=["#9cb7c2", "#4b8798", "#176b59"])
        ax.set_ylim(0, max(values) * 1.18)
        for i, value in enumerate(values): ax.text(i, value + max(values)*.03, f"{value:,}", ha="center")
        ax.set_title(title); ax.set_ylabel("Count")
    fig.suptitle("Fusion ablation: structural compression, not correctness")
    fig.tight_layout(); save(fig, "fusion_ablation")
    gates = evidence["groups"]["primary_random:test"]
    fig, ax = plt.subplots(figsize=(9, 4.7))
    gate_keys = ["nonempty", "literal", "traceable", "triage_gate"]
    names = ["Nonempty", "Literal", "Extended locator", "Conservative gate"]
    for offset, key, title, color in ((-.2, "retention", "Candidate retention", "#4b8798"),
                                    (.2, "span_positive_predictive_value", "Adequate reference spans among retained", "#176b59")):
        ax.bar([i + offset for i in range(4)], [gates[g][key] or 0 for g in gate_keys], width=.38, color=color, label=title)
    ax.set_xticks(range(4), names); ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -.15), frameon=False)
    ax.set_title(f"Evidence triage trade-off: retrospective main test (n={gates['nonempty']['n']})")
    fig.tight_layout(); save(fig, "evidence_tradeoff")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    out = (ROOT / args.run_dir).resolve()
    review, fusion, evidence = [read(out / name) for name in ("review_report.json", "fusion_comparison.json", "evidence_comparison.json")]
    rows, _ = load_jsonl(out / "review_labels_normalized.jsonl")
    evaluations, _ = load_jsonl(out / "evidence_candidate_results.jsonl")
    queue, _ = load_jsonl(out / "fusion_review_30.jsonl")
    index = {r["candidate_id"]: r for r in evaluations}
    for row in rows: row["validation"] = index[row["candidate_id"]]["validation"]
    manifest = __import__("csv")
    with (out / "manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        inputs = {r["role"]: r for r in manifest.DictReader(stream)}
    fused, _ = load_jsonl(Path(inputs["fused"]["path"]))
    names = defaultdict(set)
    for row in fused:
        for key in ("entity_1", "entity_2"): names[row[key]["name"]].add(row[key]["type"])
    diagnostics = {"literature_typed_nodes": sum(map(len, names.values())), "literature_name_only_nodes": len(names),
        "names_with_multiple_types": {name: sorted(types) for name, types in sorted(names.items()) if len(types) > 1},
        "explanation": "Existing Neo4j importer merges Entity by name only. Typed literature graph counts differ; Open Targets contributes additional names. No live database query was performed."}
    (out / "database_identity_diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {"review": review, "fusion": fusion, "evidence": evidence, "rows": rows, "fusion_queue": queue,
               "queue_hash": sha256(out / "fusion_review_30.jsonl"), "workbook_hash": inputs["workbook"]["sha256"], "run_name": out.name}
    encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    template = Path(__file__).with_name("fyp_explorer_template.html").read_text(encoding="utf-8")
    (out / "evidence_explorer.html").write_text(template.replace("__DATA__", encoded), encoding="utf-8")
    figures(out, review, fusion, evidence)
    main_stats, challenge = review["reference_statistics"]["primary_random"], review["reference_statistics"]["challenge"]
    human = review["provenance"]["mode"] == "human_confirmed_all"
    provenance_text = ("The user confirmed source-based human verification of all 400 supplied labels. Original AI reviewer metadata was retained. "
                       if human else "The source workbook identifies ChatGPT-GPT-5.6-Sol as the reviewer and describes iterative AI-assisted review. Actual human confirmation scope has not been established. ")
    provenance_text += "No independent second-review labels were supplied. All quality numbers below are statistics against the supplied reference labels; independence and specialist medical expertise are not assumed."
    support_table = markdown_table(["Sample", "n", "Direct (2)", "Partial (1)", "Unsupported (0)", "Strict", "Lenient", "Adequate spans"],
        [[name, s["n"], s["labels"]["2"], s["labels"]["1"], s["labels"]["0"], percent(s["strict_support"]), percent(s["lenient_support"]), s["span_labels"].get("yes", 0)]
         for name, s in (("Random main", main_stats), ("Challenge", challenge))])
    fusion_table = markdown_table(["Condition", "Input records", "Typed nodes", "Unique relation edges", "Weak components", "Potential conflicts", "Self-loop edges"],
        [[c, v["input_records"], v["typed_nodes"], v["unique_relation_edges"], v["weak_components"], v["conflict_pairs"], v["self_loop_relation_edges"]] for c, v in fusion["conditions"].items()])
    gates = evidence["groups"]["primary_random:test"]
    gate_table = markdown_table(["Gate", "Retained / n", "Span PPV", "Adequate-span sensitivity", "Specificity", "Strict relation support among retained"],
        [[g, f"{v['retained']} / {v['n']}", percent(v["span_positive_predictive_value"]), percent(v["adequate_span_sensitivity"]), percent(v["inadequate_span_specificity"]), percent(v["strict_support_among_retained"])] for g, v in gates.items()])
    ci, cluster = main_stats["wilson_95_strict"], main_stats["pmid_cluster_bootstrap_95_strict"]
    triage = gates["triage_gate"]
    report = f"""# Results and Discussion — SMA evidence-backed knowledge graph

Generated for the final-year dissertation on 2026-10-02. This is an evidence-based
chapter draft, not a completed university submission or independently validated
clinical resource. Run: `{out.name}`.

## 1. Evaluation scope and provenance

{provenance_text}

The study addresses three questions: source support of extraction predictions
(RQ1), the structural and semantic effects of normalization (RQ2), and source
traceability with conservative evidence triage (RQ3). These questions do not
require training a new language model. The personal implementation contribution
in this evaluation is a provenance-checked review adapter, controlled aggregation
experiments, an offset-preserving locator and triage module, a reproducible
evaluation runner, and an offline source/review explorer. PubMed, Open Targets,
the extraction LLM, embedding model and established software libraries remain
external components and must be acknowledged in the final methods chapter.

Inputs comprised 4,554 stored PubMed title/abstract records and 18,288 canonical
extraction predictions. The supplied evaluation workbook contains a random main
sample of 300 predictions and a challenge sample of 100. Protected identifiers,
texts, entities, types, relations and spans exactly matched the frozen candidate
manifest. Chinese evidence labels were normalized as a representation change;
blank entity/relation/direction subchecks were not assigned inferred values.

## 2. Extraction source support (RQ1)

{support_table}

![Reference-label distribution](figures/reference_support.png)

The random sample strict support was {percent(main_stats['strict_support'])}, with
an approximate Wilson 95% interval of {percent(ci[0])}–{percent(ci[1])}. A source-
cluster bootstrap, retaining all sampled predictions within each resampled PMID,
gave {percent(cluster[0])}–{percent(cluster[1])} (2,000 replicates; seed 20261002).
The 300 predictions originated from {main_stats['unique_pmids']} PMIDs. These
intervals describe sampling variation conditional on the reference labels; they
do not quantify reviewer bias or establish clinical correctness.

The difference between strict and lenient support is material. Partial support
includes statements requiring inference or losing conditions and should not be
advertised as fully correct graph facts. The challenge sample is deliberately
nonrepresentative and was not pooled into the population estimate. No unknown
support labels were present, which is a property of this reference dataset,
not proof that every biomedical case is unambiguous.

Review notes identify condition/strength generalization, entity-type errors and
incomplete spans as recurring issues. The workbook's error categories can overlap
and are not an exhaustive independent component assessment. Separate entity-type
or direction accuracies are unavailable because their columns were left blank.
High pipeline confidence scores are heuristic and are not measured accuracy.
The present prediction-based sample cannot measure missing relations; therefore
extraction recall and extraction F1 are not reported.

## 3. Controlled fusion comparison (RQ2)

{fusion_table}

![Controlled fusion comparison](figures/fusion_ablation.png)

All conditions used the same 18,288 extraction records and the same aggregation
implementation. Dictionary mapping was replayed against the current resource;
there were zero mapping replay or stable-field discrepancies. The semantic
condition used the saved PubMedBERT-embedding alignment output at the recorded
threshold of 0.88. This experiment isolates that output's effect; it does not
retrain the embedding model or select a new similarity threshold.

Relative to 13,697 unique raw relation signatures, dictionary normalization
reduced edges by {percent(fusion['conditions']['dictionary']['compression_vs_raw_unique_edges'])};
adding semantic alignment reduced them by {percent(fusion['conditions']['semantic']['compression_vs_raw_unique_edges'])}.
All source record counts and PMID groups were preserved. Re-aggregation of the
semantic input reproduced the canonical fused output byte for byte. Connectivity
changed, with fewer weak components and a smaller proportion outside the largest
component. These are engineering results, not evidence of biomedical identity.

Potential conflict pairs increased from 32 to 59 and self-loop relation signatures
from 0 to 13. Possible explanations include bringing genuinely related evidence
together, over-merging distinct entities, or differences in study conditions.
The experiment does not discriminate these explanations without semantic review.
Thirty uniformly sampled changed-mapping units were prepared (seed 20261002),
with original source contexts and separate dictionary/semantic judgments. Their
labels have not been supplied, so mapping accuracy remains unavailable.

A traceability example demonstrates why this distinction matters: the saved
fusion edge Nusinersen → SMN1 (TARGETS) contains a prediction whose original
second entity is SMN2 (raw record 1734; PMID 41028674). The source span names
SMN2. This is an observed change of entity identity that requires mapping review,
not a newly adjudicated error label. Original-prediction support must not be
transferred automatically to the differently named fused edge.

Node accounting uses name plus type and relation accounting preserves relation
identity. The existing Neo4j importer instead merges `Entity` nodes by name.
The literature snapshot has {diagnostics['literature_typed_nodes']} typed nodes
and {diagnostics['literature_name_only_nodes']} name-only nodes; there are
{len(diagnostics['names_with_multiple_types'])} names assigned multiple types.
Consequently these offline literature counts should not be substituted for the
historical Neo4j counts including Open Targets. This also identifies an identity
model limitation to address before claiming type-separated database semantics.

## 4. Evidence traceability and triage (RQ3)

The previous scoring component only tested evidence nonemptiness. The new module
retains source character offsets through typography/whitespace normalization,
locates ordered ellipsis fragments within a single source field, and suggests
nearby sentences for unmatched spans. Fuzzy suggestions are never automatically
accepted. A conservative eligibility gate requires traceability, lexical coverage
of both endpoints, sufficient span length and a predicate cue. Negation,
uncertainty, experimental context and ellipsis gaps trigger review. Controlled
dictionary aliases and source-defined acronyms can supply lexical endpoint forms;
embedding similarity is not used as evidence of identity.

Whole-corpus locations: {evidence['corpus_location_counts']}. Exact matching
located 15,733 records. The improved locator additionally recovered normalized
spans and 1,265 ordered-fragment spans, leaving 1,152 unlocated. Recovery of a
fragment establishes where its words came from, not whether omitted text changes
the conclusion. Original evidence is never replaced by a suggested sentence.

The internal development/test assignment is deterministic and PMID-disjoint,
including across the main/challenge groups. The four examples inspected during
onboarding were assigned to development. Rules were not optimized against test
labels; however, the workbook already existed and had undergone multiple reviews.
Results are therefore a retrospective internal evaluation, not a prospective
external benchmark. The main test subset contains {gates['nonempty']['n']} predictions.

{gate_table}

![Evidence quality–retention trade-off](figures/evidence_tradeoff.png)

The conservative gate increased adequate-reference-span PPV from
{percent(gates['nonempty']['span_positive_predictive_value'])} to
{percent(triage['span_positive_predictive_value'])}, while retaining only
{percent(triage['retention'])} of candidates. It retained {triage['tp']} adequate
spans and {triage['fp']} inadequate spans, and routed {triage['fn']} reference-
adequate spans for review. This shows enrichment at a substantial coverage cost.
Source-supported relations retained numbered {triage['strict_supported_candidates_retained']}
out of {triage['strict_supported_candidates_total']}. Evidence quality and relation
factuality must remain separate: strict relationship support among retained
predictions was only {percent(triage['strict_support_among_retained'])} against
the reference labels. The {percent(triage['span_positive_predictive_value'])}
figure cannot be presented as knowledge-graph accuracy.

The appropriate product behavior is review prioritization and transparent source
display, preserving every original record. The gate should not silently delete
flagged facts or promote eligible spans to verified facts. Negation/context
heuristics are deliberately conservative and may route valid statements to review.
No semantic entailment model was implemented in this scope.

## 5. Case analysis and inspection

The offline explorer provides keyword, PMID, sample-group, reference-support and
triage filters; each candidate opens its complete saved abstract, original span,
source highlights, review reasons and PubMed link. Mapping review records can be
entered and exported without altering the supplied workbook. Empty searches have
an explicit state. Labels shown in the browser remain reference labels until
their human provenance is established.

The companion `graph_explorer.html` exposes the complete frozen literature
graph, a bounded directed neighbourhood, entity and relation filters, potential
conflict states and every joined original evidence record. A multi-source edge
shows distinct PMIDs separately from record count, preserving repeated
predictions without calling them independent papers. Open Targets associations
carry Ensembl/disease identifiers and their source score; they are displayed in
a separate identifier namespace and do not acquire invented PubMed evidence.
This is an offline snapshot view, not a live Neo4j database measurement.

For example, SMA-RE-0001 illustrates a supported relationship with an incomplete
span in the supplied review: the fragment contains only the outcome phrase.
SMA-RE-0002 illustrates ordered fragments and the need to distinguish a gene
from the conditions under which variants are related to a phenotype. These are
reference-review examples, not new medical findings. Detailed row-level results
and original reviewer reasoning remain in the run package for inspection.

## 6. Comparison with relevant literature

BioRED provides a curated biomedical relation dataset and annotation guidelines,
illustrating the value of independently specified entity and relation annotation
[1]. Its benchmark scores cannot be directly compared with this project's
prediction-only SMA support rate because the tasks and denominators differ.
The present audit addresses source support; exhaustive document annotation would
be needed for a comparable recall evaluation.

The embedding provider describes its model as a sentence-similarity model built
from PubMedBERT and trained on medical title/abstract pairs [2]. This supports
the domain-representation choice, but does not validate a cosine threshold as an
entity-identity decision. SapBERT specifically addresses biomedical entity
representations through synonym-based self-alignment [3], motivating an
entity-linking alternative to evaluate later rather than assuming that sentence
similarity alone is sufficient.

## 7. Limitations and conclusions against objectives

RQ1: the supplied integrated labels have been validated and summarized; actual
human verification scope {'has been confirmed by the user' if human else 'remains unconfirmed'}.
Independent inter-annotator agreement and exhaustive-relation recall remain
unavailable. RQ2: controlled structural effects and provenance preservation are
demonstrated, while biomedical mapping correctness awaits the 30-unit review.
RQ3: source-offset traceability and conservative triage are implemented, tested
and retrospectively evaluated; semantic entailment remains outside this module.

The results support the feasibility of an auditable construction and inspection
workflow. They also reveal that nonempty spans, high confidence and a smaller
graph are insufficient evidence of reliable biomedical statements. The next
quality improvement should address conditions, typing and entity identity,
following actual error categories rather than adding model complexity alone.
GraphRAG, answer citation validation and claim-level support validation remain
future work and are not described as completed innovations. The tool is a
research prototype, not a clinical decision system or validated target-discovery
resource. The submitted dissertation should incorporate these measured outcomes
into its introduction/objectives, methods, project-plan review and conclusions,
and acknowledge permitted AI assistance under the applicable assessment brief.

## References and reproducibility

[1] Luo et al., BioRED: a rich biomedical relation extraction dataset (2022).
https://pmc.ncbi.nlm.nih.gov/articles/PMC9487702/

[2] NeuML, pubmedbert-base-embeddings model card (accessed 2026-10-02).
https://huggingface.co/NeuML/pubmedbert-base-embeddings

[3] Liu et al., Self-Alignment Pretraining for Biomedical Entity Representations,
NAACL 2021. https://aclanthology.org/2021.naacl-main.334/

[4] NIST/SEMATECH e-Handbook, binomial proportion confidence intervals.
https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm

Local evidence: `manifest.csv`, `run_config.json`, `review_report.json`,
`fusion_comparison.json`, `evidence_comparison.json`,
`evidence_candidate_results.csv`, `database_identity_diagnostics.json`,
`validation_summary.json`. The manifest fixes input and algorithm hashes;
the presentation manifest fixes report/UI builder hashes. No workbook, canonical
data or database was changed by this evaluation.
"""
    (out / "results_and_discussion.md").write_text(report, encoding="utf-8")
    zh = f"""# SMA 毕设评价结果与交付状态

运行：`{out.name}`。日期：2026-10-02。

## 标签口径

{'用户已确认全部400条对照摘要的人工核验。原AI评审记录保留。' if human else '原表评审者全部为 ChatGPT-GPT-5.6-Sol；人工核验范围待确认，当前指标只能称为AI辅助参考标签统计。'}
独立第二评审为空，不能报告人际一致性或把多轮AI自查称为独立人工复核。
中文合格/不合格已规范化；原始表及空白细分字段未修改。

## 抽取评价

{support_table}

严格支持与部分支持分开。Recall/F1、独立实体类型/方向准确率不可从现有材料计算。

## 融合对照

{fusion_table}

18,288条证据计数均保留，来源集合一致，语义条件复现canonical字节一致。
节点按名称＋类型计数，与Neo4j按名称合并的历史口径不同。压缩不等于正确融合。
30个变更映射单元已固定随机抽样并附原文，尚无人工判断。

## 证据验证

{gate_table}

测试主集 n={gates['nonempty']['n']}，按PMID与开发集分开。规则为回顾性内部评价。
保守筛查提高保留片段的参考合格比例，但大量合格记录也被送审。
它是待审分流，不是自动语义验证或删边依据；{percent(triage['span_positive_predictive_value'])}不是图谱准确率。

## 交付与下一步

- 英文结果与讨论草稿：`results_and_discussion.md`。
- 评价候选与融合审核界面：`evidence_explorer.html`。
- 完整图谱、局部有向关系和融合边来源：`graph_explorer.html`。
- 操作手册与实际验收记录：`USAGE_AND_ACCEPTANCE_zh.md`。
- 三张科学图：`figures/`，提供PNG与SVG。
- 融合30项：界面中选择同一实体/不同实体/无法判断，导出JSON。
- 审核导入：`python src/evaluation/summarize_fusion_review.py --queue <run>/fusion_review_30.jsonl --reviews <export.json> --output <new_report.json>`。
- 不需要重审400条；先确认真实人工核验范围。融合正确性还需要这30项新判断。

所有未取得的标签指标保持缺失，不用自动分数代替。本文不能代替完整学校最终报告；
目标、方法、文献综述、风险/伦理、真实日志、口试材料仍按课程要求整合。
"""
    (out / "summary_zh.md").write_text(zh, encoding="utf-8")
    presentation = {"builder_sha256": sha256(__file__), "template_sha256": sha256(Path(__file__).with_name("fyp_explorer_template.html")),
        "artifacts": {str(p.relative_to(out)): sha256(p) for p in [out / "results_and_discussion.md", out / "summary_zh.md", out / "evidence_explorer.html"]}}
    (out / "presentation_manifest.json").write_text(json.dumps(presentation, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "generated": ["evidence_explorer.html", "results_and_discussion.md", "summary_zh.md", "3 PNG/SVG figures"],
                      "database_typed_vs_name_only": [diagnostics["literature_typed_nodes"], diagnostics["literature_name_only_nodes"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
