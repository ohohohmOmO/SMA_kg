# FYP completion checkpoint — 2026-10-02

## Scope and status

The core construction, inspection, human-label evaluation and reporting package
is delivered. The user confirmed all 400 labels are human-assigned and ChatGPT
only assembled the workbook. The overall project is **not declared fully
complete**: incompatible alignment, mapping correctness, current database
validation and report-scope consistency remain open. No reviewer identities or
independent agreement results were fabricated.

| Step | Delivered | Remaining boundary |
| --- | --- | --- |
| Objectives and metrics | Three RQs, measures, acceptance evidence and limits in `FYP_EVALUATION_PROTOCOL_2026-10-02.md`. | Confirm course assessment brief when assembling the final submission. |
| Human review | All 400 human-assigned labels confirmed by the user; source identities checked; main/challenge and uncertainty reported. | Original formatter metadata retained. Independent second-review fields remain empty; no need to re-enter 400 labels. |
| Fusion comparison | Identical aggregation across raw/dictionary/semantic conditions; graph/provenance checks; 30 fixed mapping units with contexts. | Thirty mapping judgments; compression is not semantic accuracy. |
| Evidence improvement | Source offsets, normalized/ordered-fragment location, conservative flags; all 18,288 sidecars; PMID-disjoint retrospective internal comparison against human labels. | Semantic entailment is not implemented; the major sensitivity/retention cost remains explicit. |
| Results and discussion | English chapter draft, Chinese summary, 3 PNG/SVG figures, offline evidence/review UI, reproducibility manifests. | Integrate with the full university report and actual project records. Future modules are explicitly unimplemented. |

## Primary deliverables

Latest run directory: `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/`.
The earlier `fyp_evaluation_2026-10-02` is retained as a historical snapshot;
its unconfirmed provenance wording is superseded by the user's statement.

- `evidence_explorer.html`: offline source browsing, filters and 30-item review.
- `graph_explorer.html`: complete frozen literature graph, bounded directed
  neighbourhoods, full original source joins, conflict state and external IDs.
- `USAGE_AND_ACCEPTANCE_zh.md`: Chinese manual and 10 actual functional checks;
  not an independent user study or student logbook.
- `results_and_discussion.md`: English chapters with measured results and limits.
- `summary_zh.md`: Chinese results and next-step guide.
- `review_report.json`: supplied-label statistics, provenance gate, no fabricated
  independent agreement or component accuracies.
- `fusion_comparison.json`, `fusion_review_30.jsonl`: controlled comparison and
  fixed semantic-review material.
- `evidence_comparison.json`, `evidence_candidate_results.csv`,
  `evidence_validation_full.jsonl`: row-level experiment and corpus sidecars.
- `manifest.csv`, `presentation_manifest.json`, `validation_summary.json`,
  `verification.json`: provenance, input hashes and verification.

## Key measured outcomes

- Random main human labels: direct 79/300 (26.3%), partial 141/300,
  unsupported 80/300. Lenient support is 73.3%, not fully correct relations.
- Fusion unique relation edges: 13,697 → 13,080 → 11,155. All 18,288 evidence
  record counts are preserved; semantic re-aggregation is byte-identical.
- Locator: exact 15,733; normalized 138; ordered fragments 1,265; unlocated
  1,152. A located span does not prove the extracted relation.
- Main internal test n=202: conservative gate retains 59; adequate-span
  reference PPV 48/59 (81.4%), sensitivity 48/103 (46.6%). Strict relationship
  support among retained candidates is 24/59 (40.7%). These metrics must not
  be conflated or advertised as knowledge-graph accuracy.
- Offline literature graph has 6,684 typed nodes and 6,524 name-only nodes.
  Neo4j's name-only identity differs; historical counts include Open Targets.
- The graph browser joins all 18,288 extraction records to their fused edges
  and saved sources. The 164 Open Targets associations have a separate source
  namespace and carry no invented literature evidence.

## Minimal remaining human actions

The 400-label origin question is resolved. ChatGPT assembled the table only.

1. In the offline explorer's fusion tab, judge the changed naming steps for
   the fixed 30 units, record an actual reviewer ID, and export JSON. Unchanged
   steps need no judgment. Different/unclear requires a brief reason.
   If the browser does not download the JSON, choose `显示导出内容` and copy
   the displayed text into a UTF-8 JSON file or return that text in chat.
2. Independent review is only needed to claim inter-annotator agreement. Its
   absence is an explicit limitation, not a fabricated zero or perfect score.

Import actual fusion judgments with:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src/evaluation/summarize_fusion_review.py --queue 'artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/fusion_review_30.jsonl' --reviews '<exported-json-path>' --output '<new-report-path>'
```

The importer rejects queue/hash/identity mismatches, incomplete choices and
unjustified uncertain/different judgments. Unfinished review has null metrics.

## Assessment and further work

Specific supplied rubrics and the 2026–27 handbook conflict on weights and oral
format. The latest Moodle/FYP brief determines submission requirements. The
evaluation chapter does not replace a complete final report, genuine logbooks,
required forms or oral presentation. Planned GraphRAG, citation validation and
claim-evidence validation are not claimed complete. Incompatible alignment and
type-aware database identity are outstanding. The current preliminary DOCX still
promises the wider modules; see `FYP_READINESS_REVIEW_2026-10-02.md` for the
concrete scope correction and quality gates.
