# Engineering Hardening - 2026-06-09

This document records the requirements locked and implementation work started
after reading `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md`.

## Reference Documents

- `AGENTS.md`
- `CONTEXT.md`
- `docs/agents/PLAN.md`
- `docs/agents/ISSUE_LOG.md`
- `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`

## Pre-Improvement Baseline

Before changing pipeline code, the current canonical outputs were archived to:

- `artifacts/runs/pre_improvement_baseline_2026-06-09/`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/baseline_summary.json`

Use that manifest to compare old canonical outputs with new hardened outputs.

## Requirements Locked

The current plan is in `docs/agents/PLAN.md`. The main decisions are:

- Add a shared biomedical schema and validator rather than letting each stage
  invent entity types, relations, and confidence semantics.
- Replace fixed `computed_confidence` values with component-based confidence
  scores using LLM self-score, evidence presence, schema validity, engine
  reliability, PMID support, and multi-engine support.
- Treat BioBERT/UIE-med fine-tuning as a later supervised-learning milestone.
  First build 500-1000 review-ready gold-standard candidates and evaluate the
  current LLM/rule baseline.
- Keep topic-balanced PubMed retrieval separate from the original PubMed
  canonical output until its added records are reviewed.
- Use a biomedical embedding model for Stage 3 semantic alignment and keep the
  alignment deterministic.
- Mark relation polarity conflicts for review instead of silently merging them.

## Implemented Changes

Shared quality layer:

- `resources/biomedical_schema.json`
- `resources/entity_dictionary.json`
- `src/biomedical/schema.py`
- `src/biomedical/confidence.py`

Stage 1:

- Updated `src/crawler/api_fetcher.py` and `src/crawler/pubmed_crawler.py` to
  avoid runtime dependency installation, return non-zero on failure, support
  output arguments, and use verified TLS by default.
- Added `src/crawler/topic_clustering.py`.
- Added `src/crawler/topic_balanced_pubmed.py`.
- Topic clustering now has a script runner using biomedical embeddings,
  n-grams, and document-frequency thresholds rather than a static English
  stop-word deletion list.

Stage 2:

- Updated `src/extraction/llm_extractor.py` so the prompt requires
  `evidence_text` and model self `confidence`.
- Updated `src/extraction/local_pipeline.py` from document-level co-mention to
  sentence-level evidence windows, relation cues, negation checks, schema
  validation, and component-based confidence.
- Updated `src/extraction/run_stage2_extraction.py` to validate schema and
  evidence.
- Added `src/extraction/build_gold_candidates.py`.

Stage 3:

- Updated `src/fusion/dictionary_mapper.py` to load external dictionaries and
  normalize relation aliases.
- Updated `src/fusion/semantic_aligner.py` to use a biomedical embedding model
  by default, set HuggingFace endpoint before import, and use deterministic true
  connected components.
- Updated `src/fusion/triples_aggregator.py` to use fused confidence scoring and
  relation conflict detection.
- Added `src/fusion/run_stage3_fusion.py`.

Stage 4:

- Updated `src/database/neo4j_importer.py` to sanitize labels and relationship
  types through the biomedical schema.
- Added `src/database/run_stage4_graph.py`.

Tests:

- Added `tests/unit/test_biomedical_quality.py`.

Glossary:

- Updated `CONTEXT.md` with Biomedical Schema, Topic-Balanced Retrieval, Gold
  Standard Candidate, and Relation Conflict.

## Probe Results

Unit tests:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

Result: 5 tests passed.

Stage 2 local rule probe:

- Run directory: `artifacts/runs/stage2_local_rule_probe_2026-06-09/`
- Input slice: 200 abstracts after offset 200
- Output triples: 138
- Rejected triples: 0

Stage 2 LLM hardened probe:

- Run directory: `artifacts/runs/stage2_llm_hardened_probe_2026-06-09/`
- Input slice: first 5 abstracts
- Output triples: 18
- Rejected triples: 0
- All 18 triples include evidence text and confidence components.
- Observed confidence range: 0.874 to 0.962

Full 200-record LLM rerun was not promoted in this pass. The 5-record probe took
about 2.5 minutes, so a full 200-record run needs an explicit long-running
window.

Stage 2 gold-candidate probe:

- Run directory: `artifacts/runs/stage2_gold_candidates_probe_2026-06-09/`
- Candidate count: 50
- Purpose: validate the gold-standard candidate generator before creating the
  target 500-1000 item review set.

Stage 3 fusion probe:

- Run directory: `artifacts/runs/stage3_fusion_probe_2026-06-09/`
- Input: `artifacts/runs/stage2_local_rule_probe_2026-06-09/spacy_extracted_triples.jsonl`
- Mapped triples: 138
- Aligned triples: 138
- Fused triples: 11
- Relation conflicts: 0
- Promoted: false

Stage 4 runner probe:

- Run directory: `artifacts/runs/stage4_runner_probe_2026-06-09/`
- Neo4j skipped for this probe.
- Local graph analytics and graph viewer snapshot succeeded.

## Current State

The hardening code and probes are in place, but canonical Stage 2 and Stage 3
outputs have not been replaced by a full hardened rerun yet. This is intentional:
the new LLM extraction contract has been validated on a small sample, while the
full 200-record LLM rerun is slow and should run in a deliberate long-running
window.

Next recommended execution:

1. Run full hardened Stage 2 with a dated run directory and `--promote`.
2. Run Stage 3 runner on the promoted Stage 2 output with `--promote`.
3. Start Neo4j and run `src/database/run_stage4_graph.py` without
   `--skip-neo4j`.
4. Update this document and the original reproduction document with the final
   promoted output counts and hashes.
