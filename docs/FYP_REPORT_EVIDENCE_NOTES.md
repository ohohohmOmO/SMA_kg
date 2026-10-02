# FYP Report Evidence And Innovation Notes

## Current scope amendment after four repairs

Current evidence is `artifacts/runs/fyp_four_repairs_final_2026-10-02/` and
`docs/fyp/FYP_FOUR_REPAIRS_STATUS_2026-10-02.md`. Older figures and semantic
alignment descriptions below document the preceding baseline. Current fusion
uses typed orthographic identity (13,001 edges/9,053 literature nodes); embedding
similarity is review-only. Active Neo4j has9,218 typed/source-scoped nodes,
13,001 literature+164 external edges, verified online with original evidence.
Five preliminary submission drafts now match RQ1 extraction support/errors,
RQ2 conservative identity/fusion, RQ3 evidence/context/type screening trade-offs.
GraphRAG/generated-answer citation/atomic claim validation are future work.

The unchanged human400 dataset supplies main strict26.3%, partial47.0%; 73.3%
is lenient support. Rules/prompt were frozen before original calls; corrected
sentence boundaries replayed preserved decisions without new calls/label changes.
This is a previously-inspected retrospective PMID-disjoint paired comparison,
not an independent prospective benchmark. Combined retained30/202, strict14/55,
PPV46.7% with substantial loss and overlapping intervals. All predictions remain;
no labels transfer to rewrites, no independent agreement or recall/F1 is inferred.
Current30-unit mapping review is optional for a mapping-quality-rate claim.
Old baseline metrics/protocol do not establish current correctness.

## Historical baseline material

Date reviewed: 2026-10-02

## Purpose

This note records how the handwritten overall project structure in
`docs/fyp/project_reference/毕设总体结构-贾欧妮.pdf` maps to the
current repository. It is the reporting checkpoint for later preliminary,
interim, and final dissertation writing.

## Verified Pipeline Status

The following parts of the diagram are implemented and supported by current
code plus dated run artifacts:

- PubMed acquisition: 4,554 abstracts.
- Open Targets acquisition: 164 relationships used in the graph run.
- BERTopic plus PubMedBERT topic analysis: 67 topics.
- Full-corpus DeepSeek V4 Flash extraction: 18,347 raw LLM triples and 18,288
  canonical de-duplicated triples covering 3,656 PMIDs.
- Biomedical schema validation and confidence scoring.
- Dictionary mapping and PubMedBERT semantic entity alignment.
- Triple aggregation: 11,155 fused literature edges.
- Relation conflict detection: 59 conflicting entity pairs and 164 fused
  records marked `needs_review`.
- Neo4j graph construction: 6,648 nodes, 11,208 total relationships, and no
  isolated nodes in the recorded full run.

Primary evidence documents:

- `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`
- `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`
- `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/`
- `artifacts/runs/stage3_fusion_full_2026-06-09/`
- `artifacts/runs/stage4_graph_full_2026-06-09/`

## Red Markings To Treat As Innovation Work

The red markings in the source PDF define four innovation modules for later
reports. They must be grouped under an `Innovation` or `Original Contribution`
section, but their completion status must remain explicit.

| Innovation | Intended contribution | Current verified status | Reporting rule |
| --- | --- | --- | --- |
| 1. Evidence validation | Align generated spans to source and route potentially inadequate evidence for review. | Source-offset locator and conservative lexical triage implemented in `src/biomedical/evidence_validation.py`, with regression tests and full-corpus/internal human-label evaluation in `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/`. Fuzzy suggestions never auto-accept. The original confidence `evidence_score` remains the historical nonempty heuristic. | Claim implemented traceability/triage; do not claim semantic entailment, calibrated accuracy, clinical verification or independent double-review agreement. Human annotation origin is confirmed by the user. |
| 2. GraphRAG | Retrieve Neo4j neighbourhoods and PMID-backed evidence, construct structured context, and generate evidence-grounded answers with a safe fallback. | Not implemented in tracked source. The Neo4j graph is implemented and can serve as its foundation. | Describe the graph as implemented; describe GraphRAG as planned until an end-to-end runner and QA evaluation exist. |
| 3. Citation validation | Validate that answer citations refer to real retrieved PMID/evidence identifiers. | Not implemented in tracked source. | Do not claim citation correctness until invalid, missing, and mismatched citations are tested. |
| 4. Claim-evidence validation | Decompose an answer into claims and verify whether retrieved evidence entails each claim. | Not implemented in tracked source. | Describe as planned until claim-level labels and measured validation results exist. |

When a module becomes complete, its report status may move from `proposed
innovation` to `implemented innovation` only after the repository contains the
source, focused tests, a reproducible run artifact, and measured results.

## Human Annotation Decision

A reviewed annotation set is needed for a defensible final-year project,
although the FYP handbook does not prescribe a fixed number of annotated
records. The handbook requires quantifiable critical assessment of technical
outcomes and makes the final report a major assessed component. Without an
independent reviewed set, the project can report pipeline counts and graph
topology but cannot credibly report extraction factuality.

The 400-item workbook uses this design:

- 300 reproducible random candidates for the main factuality/precision result.
- 100 challenge candidates that over-sample lower confidence, non-exact
  evidence, and rare relation cases for error analysis only.
- 80 candidates flagged for independent second review, enabling inter-annotator
  agreement reporting.
- Four support labels: `2` directly supported, `1` partially or implicitly
  supported, `0` unsupported or contradicted, and `U` unclear.
- Separate checks for entity correctness, entity type, relation, direction,
  evidence span, error type, and corrected triple.

Main metrics must use only the 300 `primary_random` candidates. Challenge-set
results must be reported separately. Because the workbook begins from predicted
triples, it estimates factual correctness or precision. It does not establish
recall. A recall claim requires exhaustive relation annotation over a separate
sample of complete abstracts.

The generated run is:

- `artifacts/runs/stage2_gold_candidates_400_2026-10-01/`
- `outputs/fyp_gold_annotation_2026-10-01/SMA人工标注集_400条.xlsx`

The original workbook remains blank. A supplied final-review variant contains
all 400 integrated support/span judgments and was matched to the frozen source.
Its reviewer metadata identifies ChatGPT. The user clarified on 2026-10-02 that
all 400 labels were assigned by humans and ChatGPT only assembled the table.
The clarification is authoritative for annotation origin and is recorded separately
from the unchanged source metadata. It does not establish independent double review.
The new compact adapter preserves empty
component fields and reports reference statistics separately from human-confirmed
statistics. Second-review agreement remains unavailable because those fields are
empty. No new request to re-annotate all 400 records is made.

The latest run is `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/`;
the earlier unconfirmed run is preserved as a historical snapshot.
It includes raw/dictionary/semantic controls, source preservation checks, a
30-unit changed-mapping queue, evidence sidecars, an offline explorer and a
results/discussion draft. Fusion semantic correctness still requires its own
judgments. See `docs/fyp/FYP_COMPLETION_STATUS_2026-10-02.md` before claiming
completion or copying metrics into a submission.

## FYP Folder Requirements Relevant To Reporting

- The Project Specification and Preliminary Report template has an eight-page
  maximum. Its required headings are Project Description, Measurable Outcomes,
  Technical Background, References, and Work Plan.
- The Interim Report template has a twelve-page maximum. Its required headings
  are Project Outline, Work Done So Far, Conclusions From Initial Work,
  Challenges and Solutions, Work To Be Done, Revised Gantt Chart, and
  References.
- The Assessment Overview sheets supplied on 2026-10-02 assign 50% to the
  final report, 20% to the oral presentation, 15% to the interim report, 5% to
  the Project Specifications and Preliminary Report, and 10% to continuous
  student performance. These sheets total 100% and are used as the current
  working allocation. They differ from the earlier handbook summary, so the
  latest Moodle/FYP System assessment brief must still be checked before each
  submission.
- The handbook requires risk and ethical documentation and three logbook
  submissions. Logbook entries must be contemporaneous and must not be
  fabricated or backfilled as evidence of work that was not done.
- The handbook permits Generative AI only under the applicable assessment
  brief. Permitted use must be acknowledged, checked, and defensible by the
  student. AI must not fabricate project activity, data, results, references,
  decisions, or logbook records.
- The public-PubMed annotation task does not itself recruit patients, collect
  private medical data, or perform an intervention. The ethical declaration
  should still be completed with the supervisor. If another person provides
  labels, record only an agreed reviewer identifier and do not collect
  unnecessary personal information.

There is a deadline conflict inside the supplied folder: the 2026-27 handbook
lists the final report deadline as 30 April 2027 at 23:59 CST, while
`FYP_timeline.png` lists 28 April 2027 at 23:59 CST. The Moodle/FYP System and
the current assessment brief should be treated as authoritative before the
deadline is written into a report plan or logbook.
