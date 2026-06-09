# Adjudicate Stage 3 Relation Conflicts

Status: Open
Created: 2026-06-09
Stage: Stage 3
Type: Review decision

## Problem

The Stage 3 rerun completed successfully and conflict detection worked as
designed, but the 59 relation conflict records have only been marked as
`needs_review`. They have not yet received human or LLM second-pass
adjudication.

This is not a Stage 3 completion blocker. It is follow-up review work after
Stage 3 has produced a reviewable conflict set.

## Current Evidence

- Conflict file: `data/interim/relation_conflicts.jsonl`
- Conflict records: 59
- Fused records marked `needs_review`: 164
- Fused graph output: `data/processed/fused_triples.jsonl`
- Stage 3/4 reproduction report:
  `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`
- Stage 3 run directory:
  `artifacts/runs/stage3_fusion_full_2026-06-09/`

## Decision Needed

Decide how relation conflicts should be adjudicated:

- human review only,
- LLM second-pass adjudication only,
- LLM pre-review followed by human confirmation, or
- keep conflict edges in the graph as `needs_review` without adjudication.

## Proposed Path

- Build a review table from `data/interim/relation_conflicts.jsonl` plus the
  supporting fused records in `data/processed/fused_triples.jsonl`.
- Include entity pair, conflicting relations, relation polarity, supporting
  PMIDs, evidence counts, confidence components, and example evidence spans.
- Run an LLM adjudication pass only if evidence spans are available and the
  prompt requires conservative outcomes such as `accept_positive`,
  `accept_negative`, `both_context_dependent`, `insufficient_evidence`, or
  `needs_human_review`.
- Record adjudicated decisions in a new dated artifact before changing any
  canonical graph output.

## Acceptance Criteria

- A dated review/adjudication artifact exists for all 59 conflict records.
- Each conflict has a decision, rationale, reviewer provenance, and timestamp.
- If canonical graph records are changed, the change is performed through a
  dated Stage 3 rerun or explicit conflict-resolution runner with manifest and
  validation summary.
- `data/interim/relation_conflicts.jsonl` remains the source conflict set until
  an adjudicated output is explicitly promoted.

## Comments

- Current `needs_review` marking is deliberate and valid Stage 3 behavior.
- This issue should not be treated as evidence that Stage 3 failed or was only
  partially completed.
