# Engineering Hardening - 2026-06-09

This document records the requirements locked and implementation work started
after reading `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md`.

## Reference Documents

- `AGENTS.md`
- `CONTEXT.md`
- `docs/agents/PLAN.md`
- `docs/agents/ISSUE_LOG.md`
- `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md`
- `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`
- `docs/reproduction/STAGE3_PREP_2026-06-09.md`
- `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`
- `.scratch/stage3-prep/PRD.md`
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
- Treat Stage 2 canonical extraction as LLM-only. Local rules produce auxiliary
  candidates for recall analysis, review, and ablation; they are not merged into
  the main graph unless verified by an LLM or a human reviewer.
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
  sentence-level rule candidate extraction with evidence windows, relation cues,
  negation checks, schema validation, and component-based confidence.
- Updated `src/extraction/run_stage2_extraction.py` to validate schema and
  evidence, promote `extracted_triples.jsonl` as LLM-only canonical output, and
  store rule candidates separately under `data/interim/`.
- Updated `src/extraction/merge_triples.py` so the default canonical merge uses
  LLM output only, with optional explicitly verified rule candidate files.
- Added `src/extraction/verify_rule_candidates.py` for optional LLM verification
  of local rule candidates into `verified_rule_triples.jsonl`.
- Updated `src/extraction/run_stage2_extraction.py` so `--llm-limit -1` assigns
  every input abstract to LLM extraction. The current full rerun policy is
  full-corpus LLM extraction with `--chunk-size 5 --parallel-workers 32`.
- Added `src/extraction/build_gold_candidates.py`.

Stage 1-2 completion status:

- Stage 1 acquisition, topic clustering, and topic-balanced retrieval runners
  have been implemented and rerun.
- Stage 2 LLM-only extraction has been rerun across all 4554 canonical PubMed
  abstracts with 32 workers, producing 18288 validated canonical triples.
- Topic-balanced PubMed candidate promotion remains an open research decision,
  tracked in
  `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`.
- BioBERT/UIE-med fine tuning remains a later decision after gold-standard
  review, tracked in
  `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`.
- Stage 3 preparation is recorded in
  `docs/reproduction/STAGE3_PREP_2026-06-09.md`.

Stage 3:

- Updated `src/fusion/dictionary_mapper.py` to load external dictionaries and
  normalize relation aliases.
- Updated `src/fusion/semantic_aligner.py` to use a biomedical embedding model
  by default, set HuggingFace endpoint before import, and use deterministic true
  connected components.
- Updated `src/fusion/triples_aggregator.py` to use fused confidence scoring and
  relation conflict detection.
- Added `src/fusion/run_stage3_fusion.py`.
- Reran Stage 3 against the latest full Stage 2 canonical output. The promoted
  result contains 11155 fused edges and 59 relation conflict records.

Stage 4:

- Updated `src/database/neo4j_importer.py` to sanitize labels and relationship
  types through the biomedical schema.
- Added `src/database/run_stage4_graph.py`.
- Updated Stage 4 scripts to write run-directory outputs before promotion,
  verify Neo4j connectivity, write Neo4j import summaries and topology metrics,
  and promote analytics/viewer outputs only after validation passes.
- Reran Stage 4 with Neo4j reachable at the configured Bolt URI. The promoted
  run imported 11155 fused literature triples and 164 Open Targets
  relationships, then generated local analytics and the graph viewer.

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

## Stage 2 Policy Update - 2026-06-09

After discussing the two candidate strategies, the selected design is:

- Canonical Stage 2 graph input: validated LLM triples only.
- Rule output: `Rule_Candidate` triples for recall analysis, missed-triple
  discovery, gold-standard sampling, and ablation.
- Verified rule output: `LLM_Verified_RuleCandidate_<model>` triples written to
  `verified_rule_triples.jsonl`; these can be merged only through an explicit
  verified-rule input, never by default.

This avoids distilling noisy rules into the main graph while preserving their
usefulness as a quality-control and coverage tool.

## Current State

The hardening code and probes are in place. Stage 2 has now been further
stabilized so raw rule candidates are separated from canonical LLM output.

The full Stage 2 LLM-only rerun completed on 2026-06-09 with 32 workers. It
covered all 4554 current PubMed abstracts and promoted the validated LLM-only
canonical output:

- Run directory: `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/`
- Detailed report:
  `docs/reproduction/STAGE2_FULL_LLM_EXTRACTION_2026-06-09.md`
- LLM raw triples: 18347
- Canonical LLM-only triples: 18288
- Unique PMIDs with triples: 3656
- Bad JSON lines: 0
- Invalid triples: 0
- Rule candidates in this canonical run: 0

Future full Stage 2 reruns should cover all current PubMed abstracts with LLM
extraction, promote only the validated LLM file to
`data/processed/extracted_triples.jsonl`, then rerun Stage 3 on that canonical
output. The command shape is:

```powershell
python src/extraction/run_stage2_extraction.py --run-dir artifacts/runs/stage2_extraction_<stamp> --llm-limit -1 --chunk-size 5 --parallel-workers 32 --promote
```

Next recommended execution:

1. Run Stage 3 runner on the promoted full Stage 2 output with `--promote`.
2. Start Neo4j and run `src/database/run_stage4_graph.py` without
   `--skip-neo4j`.
3. Update this document and the original reproduction document with the final
   promoted output counts and hashes.
