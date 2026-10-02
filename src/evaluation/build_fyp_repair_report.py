"""Report the repaired identity condition and paired assertion screening honestly."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.evaluation.build_fyp_report import read, percent, markdown_table, figures
from src.evaluation.audit_fyp_inputs import load_jsonl
from src.evaluation.fyp_dataset import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--quality-run-dir", required=True)
    parser.add_argument("--identity-run-dir", required=True)
    args = parser.parse_args()
    out, quality_run, identity_run = [ROOT / p for p in (args.run_dir, args.quality_run_dir, args.identity_run_dir)]
    review, fusion, evidence = [read(out / n) for n in ("review_report.json", "fusion_comparison.json", "evidence_comparison.json")]
    quality = read(quality_run / "validation_summary.json")
    identity = read(identity_run / "identity_validation.json")
    baseline = read(ROOT / "artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/fusion_comparison.json")
    rows, _ = load_jsonl(out / "review_labels_normalized.jsonl")
    evaluations, _ = load_jsonl(out / "evidence_candidate_results.jsonl")
    screened, _ = load_jsonl(quality_run / "candidate_quality_results.jsonl")
    validation_index = {r["candidate_id"]: r["validation"] for r in evaluations}
    quality_index = {r["candidate_id"]: r for r in screened}
    for row in rows:
        row["validation"] = validation_index[row["candidate_id"]]
        row["assertion_screen"] = quality_index[row["candidate_id"]]
    queue, _ = load_jsonl(out / "fusion_review_30.jsonl")
    with (out / "manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        inputs = {r["role"]: r for r in csv.DictReader(stream)}
    payload = {"review": review, "fusion": fusion, "evidence": evidence, "rows": rows, "fusion_queue": queue,
               "quality": quality, "queue_hash": sha256(out / "fusion_review_30.jsonl"),
               "workbook_hash": inputs["workbook"]["sha256"], "run_name": out.name}
    template_path = Path(__file__).with_name("fyp_explorer_template.html")
    template = template_path.read_text(encoding="utf-8")
    (out / "evidence_explorer.html").write_text(template.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf-8")
    figures(out, review, fusion, evidence)
    main_stats = review["reference_statistics"]["primary_random"]
    comparison = markdown_table(["Condition", "Typed nodes", "Relation edges", "Conflict pairs", "Self loops"],
        [[name, v["typed_nodes"], v["unique_relation_edges"], v["conflict_pairs"], v["self_loop_relation_edges"]]
         for name, v in [("Raw predictions", fusion["conditions"]["raw"]), ("Dictionary", fusion["conditions"]["dictionary"]),
                         ("Historical semantic baseline (unsafe)", baseline["conditions"]["semantic"]),
                         ("Repaired typed identity", fusion["conditions"]["semantic"])]])
    headers = ["Screen", "Retained/n", "Strict supported retained/total", "Strict PPV", "Strict false accepts", "Strict positives routed to review", "Original adequate-span PPV"]
    def table(group):
        return markdown_table(headers, [[name, f"{v['retained']}/{v['n']}", f"{v['strict_supported_candidates_retained']}/{v['strict_supported_candidates_total']}",
            percent(v["strict_support_among_retained"]), v["strict_false_accepts"], v["strict_positive_loss"], percent(v["span_positive_predictive_value"])]
            for name, v in quality["metrics"][group].items()])
    database = read(out / "database_acceptance.json") if (out / "database_acceptance.json").exists() else {"status": "not_verified"}
    combined = quality["metrics"]["primary_random:test"].get("combined_screen")
    cases = []
    for row in rows:
        screen = quality_index[row["candidate_id"]]
        if row["sample_group"] != "primary_random" or screen["split"] != "test":
            continue
        retained, strict = screen["gates"]["combined_screen"], row["support_label"] == "2"
        if retained == strict:
            continue
        cases.append({"candidate_id": row["candidate_id"], "pmid": row["source_pmid"],
            "category": "strict_false_accept" if retained else "strict_positive_routed_to_review",
            "human_support_label": row["support_label"], "human_span_label": row["span_label"],
            "assertion": [row["entity_1_name"], row["entity_1_type"], row["relation"], row["entity_2_name"], row["entity_2_type"]],
            "original_evidence": row["evidence_text"], "human_notes": row["review_notes"],
            "rule_flags": screen["quality"]["flags"], "model_decision": screen["model"]["decision"],
            "model_quote_checks": screen["model"]["validation"]})
    (out / "screening_error_cases.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    discussion = (f"The combined gate retained {combined['retained']} of {combined['n']} original test predictions. Strict support among retained candidates was {percent(combined['strict_support_among_retained'])}; it retained {combined['strict_supported_candidates_retained']} of {combined['strict_supported_candidates_total']} strictly supported predictions. The other {combined['strict_positive_loss']} strict positives were routed to review, not deleted. This is selective enrichment, not correction of all predictions or a new full-graph accuracy estimate." if combined else "LLM screening was not run; no model accuracy is inferred.")
    report = f"""# Results and Discussion: identity repair and assertion screening

## Objectives and research questions

The core project constructs an auditable SMA knowledge graph from a fixed PubMed abstract corpus and Open Targets snapshot. RQ1 measures source support and recurring extraction errors. RQ2 compares raw, dictionary and conservative typed-identity fusion while preserving provenance. RQ3 tests whether evidence, context and type screening can enrich retained original predictions, and quantifies the associated coverage loss. GraphRAG answer generation and answer-level citation/claim validation are future work.

## Fixed data and human labels

The corpus contains 4,554 PubMed source records and 18,288 original predictions. The user confirmed all 400 supplied labels were human-assigned, with ChatGPT only assembling the workbook. Protected source fields match the frozen sample. The random main sample contains 300 predictions from 290 PMIDs; the 100 challenge predictions are reported separately. The original workbook is unchanged. No independent second-review agreement or exhaustive extraction recall is available.

Main strict support is {percent(main_stats['strict_support'])} (79/300), partial support 47.0% (141/300), unsupported 26.7% (80/300). Lenient support 73.3% combines strict and partial judgments; it is not fully correct accuracy. Human error-category strings include 62 condition/strength cases, 79 partial-support plus evidence cases, and several overlapping typing categories. Empty component-label fields prevent separate type/direction accuracy claims. Heuristic confidence and model self-scores are not measured accuracy.

## Identity defect and repair

The previous semantic aligner grouped embeddings by type but used a name-only global map and global name frequencies. It also formed transitive similarity components, allowing different genes and clinical subtypes to collapse. SMN1 and SMN2 have distinct NCBI Gene identifiers (6606 and 6607). The fix uses (type, name) keys and frequencies throughout. Automatic identity normalization retains punctuation, numbers and qualifiers, using only case/spacing-equivalent typed names after dictionary mapping. Similarity can produce review proposals, never automatic identities. Dictionary mapping rejects conflicting authoritative IDs and subtype changes; ambiguous context-free aliases OA and exon 7 were removed (neither occurred in this frozen corpus).

All {identity['smn2_to_smn1_corrected_endpoints']} previously observed SMN2-to-SMN1 endpoint transformations across {identity['affected_pmids']} PMIDs were restored to SMN2. No automatic alignment changes failed the typed-orthographic policy check. All 18,288 original records, evidence texts and PMID associations are preserved. This verifies the demonstrated identity defects; it does not establish all dictionary mappings are medically correct.

{comparison}

![Fusion comparison](figures/fusion_ablation.png)

The repaired graph has 13,001 literature edges and 9,053 typed literature nodes. Its larger size is expected after removing unsafe merges. The historical baseline is displayed only as a preserved reference. The raw/dictionary/repaired conditions share extraction records and aggregation implementation; the unsafe baseline used the older dictionary. Compression and connectivity are structural measures, not synonym accuracy. A new fixed 30-unit review queue belongs to the repaired condition. Pending mapping judgments remain missing; old labels cannot be transferred to changed fused facts. Explicit promotion is recorded separately with rollback snapshots.

## Controlled extraction-quality improvement

The source-offset locator remains separate from assertion screening. The additional rule screen retains complete source sentences and detects explicit population/stage, experimental-model, comparator, perturbation and modality cues. Known-name/type contradictions and ambiguous gene-symbol context are routed for review. A revised future extraction prompt requires complete exact quotations and preservation of conditions, and prohibits generalizing gene perturbations to the bare gene. That prompt has not replaced or re-extracted the canonical corpus, so no accuracy gain is attributed to it.

The model screen receives only the original assertion and title/abstract, with no human support labels or reviewer notes. It checks typed endpoints, directed relation and preservation of conditions. A direct decision is eligible only when boolean schema checks pass, missing-conditions is empty and its supporting quotation is an exact complete source sentence. Failures and partial/unclear cases fail closed. The combined gate also requires the original evidence span to pass the prior traceability gate. Model quotes are separately labelled supporting quotations; original evidence is never replaced.

Rules, prompt, model, hashes and endpoint definitions were frozen before calls in frozen_protocol.json. This is a retrospective internal paired experiment on a previously inspected dataset, using the existing PMID-disjoint development/test assignment. It is not an unseen prospective benchmark. The model produced {quality['model_requests']} decisions with {quality['model_failures']} request failures and {quality['model_schema_failures']} quote/schema failures. Invalid model outputs were preserved and excluded from acceptance.

Random main internal test:

{table('primary_random:test')}

Challenge internal test (not pooled):

{table('challenge:test')}

{discussion}

The combined strict-support cluster-bootstrap 95% interval is 30.0-63.3%, overlapping the previous evidence gate's 28.8-52.5%. This does not establish a statistically reliable improvement. Concrete errors demonstrate the remaining mechanisms. SMA-RE-0013 (PMID 38165463) was retained although the human label is partial: the quoted sentence omits the study's children/type II-III scope elsewhere in the abstract. SMA-RE-0024 (PMID 32218991) was retained despite human label 0: a tp53 pathway was interpreted as the tp53 gene. Conversely, SMA-RE-0011 is human-strict but the lexical predicate detector misses 'heralded by'; SMA-RE-0031 is human-strict from the full abstract but its original fragment lacks the disease endpoint. Thus model screening can miss document-level restrictions and entity referents, while original-span screening rejects some semantically supported assertions. All 16 strict false accepts and 41 strict positives routed to review are preserved in screening_error_cases.jsonl. These examples explain failure without revising thresholds after evaluation.

During final UI acceptance, decimal punctuation was found to truncate sentence context. A documented implementation correction replayed the same 400 preserved model responses, with no new calls or label/prompt/threshold changes. The earlier run remains historical; replay_provenance.json records the correction. Sentence segmentation still uses a heuristic; abbreviation and reference resolution limitations remain.

Span adequacy concerns the original human-labelled evidence span, not the model's newly quoted supporting sentence. Strict support uses label 2 only. Selective precision must always be reported beside retention and strict-positive loss. These screens can prioritize review and expose conditions, but cannot supply new human labels, prove new assertions correct, or justify automatic deletion. Remaining false accepts and false rejects are available by candidate ID for case analysis; no thresholds were tuned after inspecting outcomes.

## Database acceptance and visualization

Database acceptance status: {database['status']}. The importer uses a separate SMAEntity label with versioned (namespace, type, exact-name/source-ID) identity. Literature and Open Targets relationships have distinct source keys, preserving their provenance and scores. Historical Entity nodes and constraints remain untouched. Counts refer to the versioned current graph, not the sum of historical and repaired databases. Online results and all acceptance queries are recorded in database_acceptance.json when available.

The offline graph joins every repaired literature edge back to all original records and complete title/abstract sources. Open Targets nodes retain source identifiers in a distinct namespace. Full sentence contexts and review flags are shown per record. The evidence explorer shows the unchanged 400 human labels, rule reasons and separately labelled model decisions. Neither UI presents eligible/model-screened candidates as human-verified facts.

## Limitations and scope

The repaired identity policy trades aggressive compression for conservative distinctions. Its regression tests verify known failures, not all biomedical mappings. The human sample estimates support of predictions, not recall of all facts in abstracts. Rules can flag legitimate conditional statements. The model can misjudge semantics even with an exact quote. Evidence from abstracts omits full-text details. Clinical reliability, causal validity and target novelty are not established. Independent mapping review and additional prospective human evaluation would strengthen the work but are not fabricated here.

The preliminary specification and plan should promise construction, traceability, controlled fusion and selective assertion screening; GraphRAG and generated-answer citation/claim validation belong to future work. Technical analysis should discuss the identity failure, precision/retention trade-off, component-label limits and database migration evidence. This chapter is material for the final dissertation, not the complete university submission.

## Reproducibility and sources

Input hashes: manifest.csv. Fusion/promotion: {identity_run.as_posix()}. Assertion screening: {quality_run.as_posix()}, frozen_protocol.json, label_blind_requests.jsonl, model_decisions.jsonl, candidate_quality_results.jsonl and validation_summary.json. UI/figure hashes: presentation_manifest.json and graph_explorer_manifest.json. Historical experiment artifacts remain unchanged.

NCBI SMN1: https://www.ncbi.nlm.nih.gov/gene/6606/ ; SMN2: https://www.ncbi.nlm.nih.gov/gene/6607/ (checked 2026-10-02).
"""
    (out / "results_and_discussion.md").write_text(report, encoding="utf-8")
    (out / "summary_zh.md").write_text(f"# 四项修复结果\n\n实体：已恢复982次SMN2错并，保留18288条证据，当前13001条文献边、9053个类型化节点。\n\n抽取：原主集严格支持26.3%，部分支持47.0%，宽松73.3%不等于完全正确率。新增条件/类型/完整证据筛查，以下为原始候选上的回顾性内部测试。\n\n{table('primary_random:test')}\n\n数据库：{database['status']}；详见database_acceptance.json。\n\n英文结果与讨论：results_and_discussion.md。可视化：graph_explorer.html、evidence_explorer.html。30项新融合审核为可选补充质量证据，不能伪造已完成；原400项不用重新标注。\n", encoding="utf-8")
    artifacts = [out / n for n in ("results_and_discussion.md", "summary_zh.md", "evidence_explorer.html")]
    artifacts += [out / "screening_error_cases.jsonl"]
    artifacts += sorted((out / "figures").glob("*"))
    (out / "presentation_manifest.json").write_text(json.dumps({"builder_sha256": sha256(__file__), "template_sha256": sha256(template_path),
        "quality_summary_sha256": sha256(quality_run / "validation_summary.json"), "artifacts": {str(p.relative_to(out)): sha256(p) for p in artifacts}}, indent=2), encoding="utf-8")
    print("Repaired-condition report and explorer generated")


if __name__ == "__main__": main()
