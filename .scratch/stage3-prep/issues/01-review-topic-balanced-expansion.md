# Review Topic-Balanced PubMed Expansion

Status: Open
Created: 2026-06-09
Stage: Stage 1
Type: Research decision

## Problem

The Stage 1 topic-balanced PubMed retrieval step is implemented and has produced
additional candidate abstracts, but these records have not been reviewed or
promoted into the canonical PubMed input.

## Current Evidence

- Source canonical PubMed input: `data/raw/pubmed_sma_abstracts.jsonl`
- Canonical PubMed count: 4554 records
- Topic clustering output: `data/processed/clustered_abstracts.jsonl`
- Topic-balanced run:
  `artifacts/runs/stage1_topic_balanced_pubmed_full_2026-06-09/`
- Candidate output:
  `artifacts/runs/stage1_topic_balanced_pubmed_full_2026-06-09/outputs/data/raw/topic_balanced_pubmed_sma_abstracts.jsonl`
- New candidate records: 27

## Decision Needed

Decide whether the 27 topic-balanced candidates should be:

- rejected and kept only as an audit artifact,
- manually reviewed and selectively merged,
- fully promoted into a new canonical PubMed input after deduplication and
  validation, or
- used only in a later recall/balance experiment.

## Acceptance Criteria

- Record the review decision and rationale.
- If promoted, create a dated Stage 1 run artifact and update downstream Stage 2
  inputs explicitly.
- If not promoted, keep the current canonical Stage 1 and Stage 2 outputs
  unchanged and document why.

## Comments

- The current Stage 2 full LLM extraction used only the canonical 4554 PubMed
  abstracts, not the topic-balanced candidate expansion.
