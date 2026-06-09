# Build Gold Set Before Medical Model Fine Tuning

Status: Open
Created: 2026-06-09
Stage: Stage 2
Type: Research decision

## Problem

BioBERT/UIE-med fine tuning may improve extraction quality, but it is not
justified until the project has a reviewed gold-standard dataset and a measured
baseline gap against the current full-corpus LLM-only Stage 2 output.

## Current Evidence

- Stage 2 canonical policy: LLM-only
- Latest Stage 2 canonical triples: `data/processed/extracted_triples.jsonl`
- Latest Stage 2 canonical count: 18288 records
- Latest Stage 2 covered PMIDs: 3656
- Gold candidate builder: `src/extraction/build_gold_candidates.py`
- Full Stage 2 report:
  `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`

## Decision Needed

Decide whether to build a 500-1000 item reviewed gold-standard set now, and what
review protocol should be used before considering BioBERT/UIE-med fine tuning.

## Proposed Path

- Generate a candidate set from the latest Stage 2 output with source text,
  proposed triple, evidence span, schema fields, confidence components, and
  model provenance.
- Review candidates manually or with a defined adjudication process.
- Measure precision/recall failure modes against the LLM-only baseline.
- Only start model fine tuning if the reviewed evaluation shows a meaningful
  baseline gap that a supervised model can plausibly address.

## Acceptance Criteria

- A reviewed gold-standard candidate set exists before any fine tuning work.
- The decision to fine tune or not fine tune is recorded with measured evidence.
- Stage 3 does not depend on fine tuning; it proceeds from the latest Stage 2
  canonical triples.

## Comments

- This issue should not block Stage 3 fusion unless the user explicitly decides
  to rebuild Stage 2 from a newly promoted or reviewed dataset first.
