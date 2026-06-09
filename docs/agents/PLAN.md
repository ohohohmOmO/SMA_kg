# Project Plan

This file is the first checkpoint before running commands, tests, scripts, or
pipeline steps in this repository.

For a dated snapshot of the implementation state on 2026-06-08, see
`docs/PROJECT_HANDOFF_2026-06-08.md`. It is reference material, not a mandatory
preflight document.

## Current Operating Rules

- Use conda environment `KG_SMA_env`.
- Run Python commands from the repository root unless a script documents another
  working directory.
- Check `docs/agents/ISSUE_LOG.md` before diagnosing any failure.
- After a successful fix, append the symptom, cause, fix, and verification to
  `docs/agents/ISSUE_LOG.md`.
- When context is compacted, memory is uncertain, or the current development
  state is unclear, reread the reference documents listed below before acting.

## Reference Documents For Current Work

Read these when starting, resuming after compaction, or resolving uncertainty:

- `AGENTS.md`
- `docs/agents/PLAN.md`
- `docs/agents/ISSUE_LOG.md`
- `CONTEXT.md`
- `docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`

The pre-improvement baseline archive was created before the 2026-06-09 hardening
work:

- `artifacts/runs/pre_improvement_baseline_2026-06-09/`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/README.md`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/manifest.csv`
- `artifacts/runs/pre_improvement_baseline_2026-06-09/baseline_summary.json`

## Runtime Requirements

- Python environment: `KG_SMA_env`
- Dependency source: `requirements.txt` plus observed runtime imports
- Required for LLM stages: `SILICONFLOW_API_KEY`
- Required for Neo4j stages: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Recommended for HuggingFace downloads: `HF_ENDPOINT=https://hf-mirror.com`
- Neo4j service must be reachable for database import and topology evaluation.

Real secrets must stay in the ignored local `.env` file. Do not write real API
keys or passwords to source code, committed docs, test fixtures, logs, manifests,
or generated examples.

## Pipeline Shape

1. Data acquisition from Open Targets and PubMed.
2. Topic clustering and topic-balanced PubMed expansion.
3. LLM/NLP extraction of biomedical triples.
4. Semantic fusion, entity alignment, relation alignment, and conflict
   detection.
5. Neo4j import plus graph analytics and visualization.
6. Evaluation, ablation study, and novelty discovery.

## Output Naming And Promotion Rules

- Canonical outputs stay under `data/` and `docs/graph_viewer.html` only after
  validation passes.
- Every rerun writes dated artifacts under `artifacts/runs/<stage>_<date-or-stamp>/`.
- Every run directory should contain at least `manifest.csv`,
  `validation_summary.json` or equivalent, logs, and output snapshots.
- Current canonical outputs must be archived before broad pipeline changes.
  The current baseline is
  `artifacts/runs/pre_improvement_baseline_2026-06-09/`.
- New experimental outputs must be named by stage and purpose, for example
  `topic_balanced_pubmed_sma_abstracts.jsonl`, not loose ad hoc filenames.
- Promotion from run artifacts to canonical paths must be explicit and must only
  happen after schema and count validation.

## 2026-06-09 Engineering Hardening Requirements

This plan is based on
`docs/reproduction/STAGE1_DATA_ACQUISITION_REPRO_2026-06-08.md` and the user
requirements from 2026-06-09.

### Shared Quality Layer

- Add a shared biomedical schema for entity types, relation types, relation
  aliases, relation polarity, and conflict pairs.
- Add an extraction validator that rejects or normalizes illegal entity types,
  illegal relations, empty entities, empty PMIDs, malformed confidence fields,
  and weak evidence.
- Add a confidence scorer. `computed_confidence` must no longer be a fixed
  literal. It should combine LLM self-score when present, evidence span
  presence, schema validity, extraction engine reliability, PMID support, and
  multi-engine support.
- Store confidence components beside the final score when practical so later
  evaluation can audit why a score was assigned.

### Stage 1: Acquisition And Topic Balance

- Keep the existing Open Targets and PubMed acquisition outputs stable, but make
  future acquisition reruns write manifests and return non-zero on failure.
- Replace notebook-only topic clustering with a script-level runner.
- Do not use a hard-coded broad English stop-word list that blindly removes
  words such as `and` or `were`. Use a domain-aware topic representation:
  biomedical embeddings for document semantics, `ngram_range` for phrase
  discovery, frequency thresholds such as `min_df`/`max_df`, and no static
  semantic word deletion by default.
- After BERTopic/topic clustering, provide a topic-balanced PubMed retrieval
  step. Underrepresented topics should generate explicit PubMed queries from
  topic terms, save fetched candidates to a dated run directory, and avoid
  duplicate PMIDs.
- Do not silently overwrite `data/raw/pubmed_sma_abstracts.jsonl` with expanded
  topic data. Save expansion outputs separately first; promote only after review.

### Stage 2: Extraction

- Confirmed decision on 2026-06-09: Stage 2 canonical extraction is LLM-only.
  Rule-based extraction must not be merged into the main graph by default.
  Rules are auxiliary candidate generators for recall analysis, missed-triple
  detection, gold-standard sampling, and ablation. A rule-derived triple may
  enter the canonical output only after LLM verification or human review.
- Update LLM extraction prompt and parsing so the model returns `confidence` and
  `evidence_text` for each triple.
- Replace fixed LLM and local-rule confidence literals with the shared
  confidence scorer.
- Add an extraction post-validator and rejected-output file for invalid entity
  types, invalid relations, empty entities, empty evidence, malformed confidence,
  and unsupported schema.
- Rename the local rule output conceptually from fallback extraction to rule
  candidate extraction. It should use sentence-level evidence windows, relation
  cues, simple negation checks, and schema validation, but its output is not
  canonical graph evidence until verified.
- Keep the existing Stage 2 chunk/resume/promote runner, but route outputs
  through the shared validator and confidence scorer. Promotion must set
  `data/processed/extracted_triples.jsonl` to the validated LLM output, not to a
  merge of LLM plus rules.
- Full Stage 2 reruns must assign all current PubMed abstracts to LLM extraction
  by using `--llm-limit -1`. Do not fall back to a 200-abstract LLM window for
  canonical runs.
- Same-key SiliconFlow parallel extraction is supported after the 2026-06-09
  probe. Use `--chunk-size 5 --parallel-workers 32` for the current full Stage 2
  rerun. If rate limits, repeated API errors, or unstable chunk validation
  appears, keep the same run directory and resume with lower parallelism rather
  than reducing LLM coverage.
- Store rule candidates under `data/interim/rule_candidate_triples.jsonl` or the
  current run directory. Store LLM/human-accepted rule candidates separately as
  `verified_rule_triples.jsonl` if that workflow is used.
- BioBERT/UIE-med fine-tuning is not an immediate production step. First build
  a 500-1000 item gold-standard candidate set with source text, proposed triple,
  evidence span, schema fields, model/rule provenance, and review status. Fine
  tuning becomes justified only if evaluation shows the LLM/rule baseline is
  too weak for the target precision/recall.

### Stage 3: Fusion And Alignment

- Ensure Stage 3 consumes the latest Stage 2 canonical output or explicitly
  records which Stage 2 run snapshot it consumed.
- Move hard-coded dictionaries out of Python and into versioned resource files.
- Use a biomedical embedding model for semantic entity alignment by default
  instead of a generic model.
- Make entity semantic alignment deterministic and implement true connected
  components over the similarity graph.
- Align relation types as well as entity names. Relation aliases must collapse
  semantically equivalent labels such as `TREATS_MENTION`, `TREATED_WITH`, and
  `TREATED_BY` into a canonical relation where appropriate.
- Add conflict detection. If the same meaningful entity pair has both positive
  and negative polarity relations, mark the fused record or conflict report as
  `needs_review` instead of hiding the disagreement.

### Stage 4: Database And Graph

- Continue to use deterministic local graph analytics.
- Add a Stage 4 runner that loads ignored local env files, validates Neo4j
  credentials, checks service reachability, runs import, runs topology
  evaluation, and writes a manifest.
- Sanitize Neo4j labels and relationship types before dynamic Cypher
  construction.
- When Neo4j is running on the configured Bolt URI, rerun import and topology
  evaluation and archive the outputs in the Stage 4 run directory.

## Execution Order

1. Archive current canonical outputs. Completed:
   `artifacts/runs/pre_improvement_baseline_2026-06-09/`.
2. Update this plan and `AGENTS.md` with the fixed requirements and recovery
   rules.
3. Add shared schema, confidence scoring, and validation modules plus resource
   files.
4. Implement Stage 1 topic clustering and topic-balanced retrieval runners.
5. Update Stage 2 LLM extraction, rule candidate extraction, optional rule
   candidate verification, LLM-only canonical merge validation, and gold-set
   candidate generation.
6. Update Stage 3 dictionary loading, relation alignment, medical semantic
   alignment, deterministic connected components, aggregation confidence, and
   conflict detection.
7. Update Stage 4 Neo4j runner and Cypher sanitization.
8. Run focused tests and script-level dry checks. Rerun full stages only when
   external services are ready and validation gates pass.
9. Update reproduction docs and issue log entries for resolved problems.
10. Stage and commit completed file-changing work before the final response.

## Before Each Run

- Confirm `conda activate KG_SMA_env` or use
  `C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe` directly.
- Confirm any required external service or API key for the script being run.
- Confirm input/output paths under `data/` match the intended pipeline phase.
- Prefer focused script-level verification before running the full pipeline.
- If a script writes canonical output, ensure there is a dated run artifact and a
  validation gate before promotion.
