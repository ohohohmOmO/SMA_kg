# Stage 3 Preparation PRD

Status: Open
Created: 2026-06-09
Owner: Local markdown issue tracker

## Goal

Prepare Stage 3 fusion, alignment, and conflict detection to consume the latest
full-corpus Stage 2 LLM-only extraction output without accidentally relying on
stale fused or aligned artifacts.

## Current Inputs

- Stage 1 canonical PubMed abstracts:
  `data/raw/pubmed_sma_abstracts.jsonl`
- Stage 1 topic clustering:
  `data/processed/clustered_abstracts.jsonl`
- Stage 2 canonical LLM-only triples:
  `data/processed/extracted_triples.jsonl`
- Stage 2 full run report:
  `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`
- Stage 3 preparation report:
  `docs/reproduction/STAGE3_PREP_2026-06-09.md`

## Non-Goals

- Do not promote topic-balanced PubMed expansion into canonical PubMed input
  without review.
- Do not train or fine tune BioBERT/UIE-med before a reviewed gold-standard
  candidate set exists.
- Do not treat current `mapped_triples.jsonl`, `aligned_triples.jsonl`, or
  `fused_triples.jsonl` as up to date until Stage 3 is rerun against the latest
  Stage 2 output.

## Acceptance Criteria

- Open Stage 1 and Stage 2 research decisions are tracked as implementation
  issues under this PRD.
- Stage 3 run plan names the exact Stage 2 input and stale artifacts to replace.
- Future Stage 3 work records consumed input paths, hashes, output paths, and
  validation results in a dated run directory.
