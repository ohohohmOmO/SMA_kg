# SMA FYP evaluation protocol

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

Date: 2026-10-02. Scope: complete the existing construction project through
evaluation and evidence traceability, then write results and discussion. This
does not add GraphRAG or claim-level semantic validation to the completed scope.

## Objectives and acceptance evidence

| Research question | Objective | Measures and deliverables | Completion boundary |
| --- | --- | --- | --- |
| RQ1 Extraction | Quantify source support of the frozen extraction predictions. | Main random sample n=300; challenge n=100 separate; strict/lenient support, unknown counts, evidence adequacy, Wilson and PMID-clustered intervals, errors. | Validate candidate identity and integrated labels. Human attribution requires confirmation of the actual human review scope; model labels remain model-assisted reference labels until then. |
| RQ2 Fusion | Isolate dictionary and semantic normalization effects. | Three conditions on the same 18,288 records, identical aggregation; typed nodes, relation-specific edges, graph connectivity, changed mappings, provenance preservation. | Structural effects measured automatically. Biomedical mapping correctness requires separate mapping judgments; extraction labels cannot supply these. |
| RQ3 Evidence | Improve evidence traceability and route potentially inadequate spans for review. | Nonempty baseline, literal-match baseline, normalized/ellipsis locator, endpoint-coverage gate; source offsets, flags, coverage, reference-label agreement, correct/incorrect retention. | Implemented locator and triage are not semantic entailment, calibrated medical confidence or clinical validation. |
| Reporting | Produce a reproducible evidence package. | Hash manifest, exact configurations, row-level outputs, plots, offline evidence explorer, results/discussion draft, focused regression tests. | No invented human labels, independent agreement, recall, F1, medical conclusions or unfinished-module results. |

## Fixed inputs and sequence

1. Freeze objectives, measures and inference limits in this file.
2. Preserve and validate the supplied `SMA人工标注集_400条_最终全表复核版.xlsx`.
   Its protected candidate fields match the original 400-item manifest.
   The source records identify `ChatGPT-GPT-5.6-Sol` as reviewer and describe
   AI-assisted review. In a subsequent 2026-10-02 clarification, the user stated
   that all 400 labels are human-assigned and ChatGPT only assembled the table.
   This clarification is recorded in the new human-confirmed run without
   overwriting original workbook metadata.
   Blank per-component columns do not become automatically assigned labels.
3. Compare saved raw/mapped/aligned snapshots with identical aggregation. Check
   row-level PMID, relation, evidence and type preservation before comparison.
4. Implement fixed traceability rules without fitting thresholds to the final
   reference labels. Use synthetic regression fixtures; report retrospective
   evaluation limitations. A deterministic PMID-disjoint development/test split
   is recorded. The first four inspected candidate PMIDs are development only.
5. Generate results and discussion directly from the run's JSON/CSV outputs.
   Conclusions state unresolved evidence explicitly rather than filling gaps.

## Metrics and interpretation

- Strict support: label 2 / labels 0,1,2. Lenient support: labels 1 or 2 /
  labels 0,1,2. Also report U / all, confirmed support / all and U bounds.
- Evidence adequacy uses the separate evidence label, not the relation label.
- Evaluation of an evidence gate: positive predictive value, sensitivity to
  adequate reference spans, specificity, false-accept/false-reject counts and
  candidate retention. These are span-classification metrics; they are not
  extraction recall. Extraction support among retained candidates is separate.
- Main and challenge groups remain separate throughout. Test metrics are
  labelled retrospective internal results against the supplied reference.
- Wilson intervals assume approximately independent predictions. PMID-cluster
  bootstrap resamples source abstracts and keeps their associated predictions;
  report seed and replication count. Neither repairs annotation bias.
- Confidence is a heuristic score. Do not call it measured accuracy or a
  calibrated probability. No score threshold is selected from test labels.
- A reduction in nodes/edges measures compression, not biomedical correctness.
- Conflict flags identify potential incompatible polarity, not proved medical
  contradictions. Unreviewed flags remain unresolved.

## Human work kept minimal

The supplied 400 labels are reused; no request to re-annotate 400 records is made.
All 400 were confirmed as human-assigned by the user on 2026-10-02, with ChatGPT
performing workbook assembly only. The new run records the actual statement
without changing original metadata. Second-review agreement stays unavailable
without genuinely independent reviews; the confirmation does not supply them.

Prepare a fixed 30-unit fusion queue with source contexts, plus an offline
two-choice/uncertain review interface. These judgments cannot be manufactured
from embeddings or copied extraction support. Keep automatic structural results
and pending semantic results separate.

## Reproducibility and promotion

The runner creates a new run directory and refuses to overwrite it. It never
changes canonical data, the supplied workbook, or Neo4j. An improved evidence
sidecar is generated for every raw extraction record, with versioned rule and
configuration metadata. The existing graph remains available; the new offline
explorer provides source tracing and review. Promotion is unnecessary for this
evaluation package and requires a separate, validated decision if later wanted.
