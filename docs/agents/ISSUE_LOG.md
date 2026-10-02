# Issue Log

Read this file before diagnosing failures. When a problem is successfully
resolved, append a new entry with the date, symptom, cause, fix, and
verification.

## Entry template

```md
### YYYY-MM-DD - Short title

- Symptom:
- Cause:
- Fix:
- Verification:
```

## Resolved issues

### 2026-10-02 - Inline GraphRAG audit indexed a source-sentence generator

- Symptom: Read-only audit stopped with TypeError after snapshot/live retrieval
  had already matched; citation/control-flow checks had not run.
- Cause: The audit harness used list indexing on source_sentences, which yields
  a generator. No product-code defect was established.
- Fix: Used next(source_sentences(...)) in the explicitly synthetic fixture.
  Product modules, canonical inputs and database were not changed.
- Verification: Eight synthetic citation/answer-routing checks passed without
  model API calls. Real snapshot and Neo4j retrieval matched the active repaired
  graph. Boundaries and module hashes recorded in GRAPHRAG_MODULE_AUDIT_2026-10-02.

### 2026-10-02 - FYP notes treated conflicting assessment sources as a confirmed replacement

- Symptom: Central assessment notes called 5/15/10/20/50 confirmed and inferred
  no assessed poster percentage, whereas the 2026–27 handbook states
  10/5+10/10/25/40 with a 30/70 poster/oral split.
- Cause: Separate-sheet filenames and receipt order were taken as evidence of
  applicable version without reconciling handbook pages 5–6, 11–13, 24 and 27.
- Fix: Corrected central notes to show both schemes and retain the unresolved
  official-version decision; added the crosscheck and PLAN pointer. External
  drafts still need harmonisation after confirmation; no approval is inferred.
- Verification: Read original handbook/all five sheets and viewed timeline and
  preliminary plan page. Also found the schedule-table/Gantt gap; revalidated
  frozen 400 labels, full fusion and expected database identities offline;
  all 56 tests passed. Artifacts: fyp_requirements_crosscheck_2026-10-02.

### 2026-10-02 - Audit document patch repeated one target in an atomic patch

- Symptom: Initial document patch was rejected before changing tracked files.
- Cause: A delete and add operation named the same assessment file in one patch.
- Fix: Added the new report separately and used a single Update operation for
  the existing assessment note.
- Verification: Initial git status showed only the new audit artifact directory;
  corrected operations succeeded. Final diff checks verify the authored files.

### 2026-10-02 - Similarity alignment merged distinct identities and overwritten types

- Symptom: Gene SMN2 was converted to SMN1 at982 endpoints/618 PMIDs;
  SMA subtypes changed and a shared Gene/Protein name overwrote typed mappings.
- Cause: Embedding similarity/connected components were treated as identity;
  map and frequency keys used names without types.
- Fix: Type/name keys and frequencies, authority/subtype dictionary guards,
  conservative orthographic identity; semantic proposals review-only. Removed
  context-free OA/exon7 mappings. Validated then promoted new fusion with backups.
- Verification: Full18,288 source rows preserved; all982 endpoints restored;
  13,001 edges/9,053 typed nodes; identity_validation.json and five identity tests.

### 2026-10-02 - Name-only database identity and shared-source relationships lost distinctions

- Symptom: Legacy Entity.name merge disagreed with typed graph evaluation,
  and shared relationships allowed external data to overwrite literature evidence.
- Cause: Name-only node constraint and source-independent relation identity.
- Fix: Versioned SMAEntity keys with type/source namespace, source-specific
  edge keys and complete original assertion records; activate after full online
  acceptance. Historical Entity nodes/constraints preserved; clear disabled.
- Verification: Current typed-v2-8a4dbccd4fdc22ca9,218 nodes/13,165 edges,
  full property reconciliation and18,288 evidence records; legacy6,648/11,208
  unchanged. Source/typed regression tests pass. Read-only current audit passes;
  prior repaired-version repeat import also reconciles idempotently.

### 2026-10-02 - Source sentence heuristic truncated statistics at decimal points

- Symptom: Browser showed '01), and a decreased heart rate ( P < .' as context.
- Cause: Sentence regex split at every dot, including .05/.01 and variant notation.
- Fix: Boundaries now require whitespace/newline and retain exact source offsets;
  corrected frozen experiment replays identical400 model responses, no new calls,
  prompt/threshold/label changes. New graph sidecar version fully reconciled online.
- Verification: Decimal-context regression and56 total tests pass; browser shows
  complete RESULTS sentence at abstract[523,705). Replay provenance preserved;
  combined result30/202 with14/55 strict positives unchanged. Original run retained.

### 2026-10-02 - PyVis platform-default encoding failed on Windows

- Symptom: Full Stage4 local export raised UnicodeEncodeError for © under GBK
  after database acceptance and analytics had succeeded.
- Cause: PyVis write_html used platform default encoding.
- Fix: Generate HTML then explicitly write UTF-8; stage runner metadata now
  reports actual historical-preservation policy regardless of legacy CLI flag.
- Verification: Failed run retained; focused verified Stage4 local rerun succeeded,
  typed MultiDiGraph metrics and UTF-8 PyVis snapshot produced with valid=true.

### 2026-10-02 - Report draft promises and Word pagination diverged from core scope

- Symptom: Five supplied drafts still promised unbuilt answer-generation modules;
  expanded ethics text moved signatures onto an otherwise empty third page.
  Packaged renderer lacked pdf2image in KG_SMA_env/LibreOffice in runtime.
- Cause: Original proposal scope exceeded measured core; preserved form had a
  limited page budget and packaged render dependencies were unavailable.
- Fix: Align goals/RQs/plan to extraction, identity and assertion screening;
  keep three answer modules future work and historical logbook entry. Compact
  ethics prose; hidden installed Word COM PDF export and bundled Poppler fallback.
- Verification: All23 final pages inspected (5/4/2/4/8), including both ethics
  signature rows; preliminary8 pages/technical4/workplan1. Original drafts backed
  up, source/revised hashes checked before five FYP promotions. No approval,
  signatures, independent labels or student personal activity fabricated.

### 2026-10-02 - Human annotation origin was mistaken for workbook formatter metadata

- Symptom: The first evaluation conservatively labelled the 400 supplied labels
  unconfirmed/AI-assisted because every source reviewer ID named ChatGPT.
- Cause: That metadata alone did not establish who assigned the labels. The user
  subsequently clarified that all 400 are human-assigned and ChatGPT assembled
  the table only.
- Fix: Recorded the actual user attestation without changing the source XLSX;
  generated a new human-confirmed run and updated active reporting/status docs.
  Original artifacts remain historical; independent second review is not inferred.
- Verification: New report exposes human-confirmed statistics, preserves source
  fields and workbook bytes, removes the pending origin request, and reproduces
  previous numerical results and the same 30-unit fusion queue.

### 2026-10-02 - Supplementary verification code paths had duplicate slash aliases

- Symptom: The older verification JSON contained two builder entries using
  backslashes and forward slashes, with different hashes after figure formatting.
- Cause: An incremental verification update inserted a new slash-style key
  without replacing its older alias.
- Fix: The new human-confirmed run records supplemental code paths using one
  normalized slash convention and verifies each recorded hash before delivery.
  The old dated snapshot is preserved; its presentation manifest is the
  authoritative builder/report record for that historical run.
- Verification: Normalized keys are unique and match current files in the new
  verification JSON; inputs, measured outputs and source workbook are unchanged.

### 2026-10-02 - Generated SVG path whitespace failed staged diff checks

- Symptom: `git diff --cached --check` reported trailing whitespace in the
  three generated scientific SVG figures.
- Cause: Matplotlib serializes multiline SVG path coordinates with trailing
  spaces; they are harmless to rendering but fail the repository diff check.
- Fix: The figure builder removes end-of-line whitespace after SVG export,
  retaining newline separators and all path coordinates. Regenerated figures
  and updated their verification hashes.
- Verification: XML parsing succeeds and staged diff whitespace checks pass.

### 2026-10-02 - Compact final-review workbook needed a provenance-preserving adapter

- Symptom: The supplied final workbook uses integrated support labels and Chinese
  span labels, while the detailed original protocol expects component checks and
  independent reviewer/adjudication fields. Optional OOXML metadata inspection
  also raised `KeyError` for absent `docProps/core.xml`.
- Cause: The revised workbook has a different review protocol and does not
  require optional package metadata. Empty component fields and AI reviewer
  metadata cannot be interpreted as completed independent human reviews.
- Fix: Added a separate compact-label adapter with protected candidate/source
  checks; normalized span labels without inventing component judgments. Treated
  OOXML package metadata as optional during inspection. Preserved the source
  workbook and recorded pending human confirmation explicitly.
- Verification: All 400 protected candidates match; integrated labels parse;
  original workbook SHA-256 remains unchanged. Regression tests cover label
  normalization, tampered identities and missing human provenance.

### 2026-10-02 - Browser download completion could not be verified for review export

- Symptom: The in-app browser automation timed out while waiting for a blob JSON
  download completion event. The actual download completion was not established.
- Cause: The current browser-tool event capture did not provide a completed
  download result for this local export; no claim is made that browser downloads
  themselves are broken.
- Fix: Added a visible, selectable JSON text export alongside the download
  button, using the same export schema and queue hash. This provides a copy/save
  route independent of download-event capture.
- Verification: A clearly marked synthetic queue in a separate storage namespace
  retained its one synthetic review after reload. The text export parsed as
  `sma_fusion_review_v1` with the expected synthetic queue hash, protected mapping
  and judgment. No real fusion judgments were created. Temporary fixture and
  browser tabs were removed after verification.

### 2026-10-02 - Bundled DOCX renderer could not find LibreOffice

- Symptom: The packaged `render_docx.py` stopped before rendering the updated
  FYP Roadmap because `soffice.exe` was not available on the bundled runtime
  PATH.
- Cause: The installed Codex primary-runtime bundle includes the document
  renderer and Poppler but no LibreOffice executable.
- Fix: Used Microsoft Word's installed COM export in headless mode to create a
  temporary PDF, then rasterized it with the bundled Poppler for the required
  page-by-page visual review.
- Verification: The updated five-page Roadmap rendered successfully; all five
  page images were inspected with no clipping, overlap, missing glyphs, broken
  tables, or page-number defects.

### 2026-10-02 - Current human-review workbook had no compatible offline report

- Symptom: The current 400-item workbook could not be evaluated through the
  historical `metrics_calculator.py`, which expects a different scored CSV
  and uses a fixed LLM fallback score when its API key is absent.
- Cause: The historical scorer predates the primary/challenge sampling,
  independent human reviews, unknown labels and adjudication fields.
- Fix: Added a separate read-only offline reporting entrypoint for the current
  workbook with sample-identity checks, separate groups, explicit unknown
  denominators and pre-adjudication human agreement. The legacy scorer is
  explicitly excluded from this workflow; its code is not changed.
- Verification: The initial 400-pending workbook reports null quality metrics
  and zero final reviews without API calls; all 18 unit tests passed,
  including incomplete-review, unknown-label and adjudication cases.

### 2026-10-02 - FYP document inspection used incompatible console encoding

- Symptom: A read-only OOXML inspection printed garbled Chinese and stopped
  with `UnicodeEncodeError` when it encountered a bullet character.
- Cause: Python stdout defaulted to GBK while the PowerShell tool output
  expected UTF-8; PowerShell pipeline input encoding was also implicit.
- Fix: Set `PYTHONIOENCODING=utf-8` and PowerShell `$OutputEncoding` to UTF-8
  for document-inspection commands using the required `KG_SMA_env` Python.
- Verification: Repeated extraction of the FYP Roadmap and four submission
  drafts completed with exit code 0 and readable Chinese, bullets and tables.

### 2026-10-01 - Legacy FYP form templates lacked built-in Word styles

- Symptom: The FYP submission-pack generator stopped with `KeyError: no style
  with name 'Title'`, then with the same error for `List Bullet`, while editing
  the supplied risk and logbook templates.
- Cause: The legacy university Word templates contain a restricted custom style
  set and do not include every built-in style expected by a new blank DOCX.
- Fix: Made heading styles conditional and generated bullets/numbering with
  explicit paragraph formatting instead of assuming built-in list styles.
  Preserved the original form layouts and compacted gateway-answer cells to
  prevent pagination drift.
- Verification: Microsoft Word rendered the final pack successfully as 5, 4,
  2, 3 and 8 pages respectively; every rendered page was visually inspected,
  and the preliminary report meets its eight-page limit with four pages of
  technical background.

### 2026-06-09 - Neo4j relationship sanitizer allowed schema-external relation tokens

- Symptom: The new unit test for Neo4j dynamic Cypher sanitization failed
  because `safe_relationship_type("bad rel`) DELETE r //")` returned
  `BAD_REL_DELETE_R` instead of falling back to `ASSOCIATED_WITH`.
- Cause: `safe_relationship_type` normalized arbitrary text into a Cypher-safe
  token after schema normalization failed, so schema-external relation names
  could still become dynamic relationship types.
- Fix: Changed `safe_relationship_type` to accept only relations that normalize
  through the biomedical schema; all schema-external values fall back to
  `ASSOCIATED_WITH`.
- Verification: `python -m py_compile src/database/neo4j_importer.py
  tests/unit/test_biomedical_quality.py` passed; `python -m unittest discover -s
  tests/unit -v` passed 10 tests.

### 2026-06-09 - Stage 2 canonical LLM coverage was limited to 200 abstracts

- Symptom: A full rerun request still used the historical `--llm-limit 200`
  setting, which would make the new LLM-only canonical Stage 2 output cover only
  the first 200 PubMed abstracts.
- Cause: The Stage 2 runner inherited the old design where LLM handled a
  200-abstract high-precision window and local Regex/rule fallback handled the
  remaining abstracts. After rules were demoted to auxiliary candidates, that
  default no longer matched the canonical LLM-only policy.
- Fix: Updated `src/extraction/run_stage2_extraction.py` so `--llm-limit -1`
  means all input abstracts and made it the default. Updated README, PLAN, and
  reproduction docs to use full-corpus LLM extraction with
  `--chunk-size 5 --parallel-workers 32`.
- Verification: `python -m unittest discover -s tests/unit -v` passed 8 tests;
  `artifacts/runs/stage2_extraction_llm_all_32w_2026-06-09/` completed with
  `llm_limit_effective=4554`, `parallel_workers=32`, 18347 validated raw LLM
  triples, 18288 canonical LLM-only triples, 0 bad JSON lines, and 0 invalid
  triples.

### 2026-06-09 - Stage 2 rule candidates could enter canonical graph output

- Symptom: Stage 2 discussions identified that local rule extraction is too
  coarse to be merged with LLM triples as canonical graph evidence; the old
  merge path could combine LLM output with raw rule/Regex output.
- Cause: The historical Stage 2 design treated local rules as a fallback
  extractor and merged their output into `data/processed/extracted_triples.jsonl`
  by default.
- Fix: Locked Stage 2 canonical extraction to LLM-only output, renamed local
  rules to `Rule_Candidate`, moved rule outputs to `data/interim/`, added an
  optional LLM verifier for rule candidates, and changed the default merge entry
  point to include only LLM plus explicitly verified rule files.
- Verification: `python -m py_compile` passed for the updated Stage 2 scripts;
  `python -m unittest discover -s tests/unit -v` passed 7 tests; the
  `artifacts/runs/stage2_rule_candidate_policy_probe_2026-06-09/` dry run
  produced 5 rule candidates and verifier dry-run coverage with 0 missing
  source abstracts.

### 2026-06-09 - Stage 1 crawlers used insecure TLS and runtime installs

- Symptom: Stage 1 diagnosis found `verify=False`, runtime `pip install` calls,
  hard-coded output paths, and swallowed failures in crawler scripts.
- Cause: The original crawler scripts were written as ad hoc runnable scripts
  rather than reproducible pipeline entrypoints.
- Fix: Updated Open Targets and PubMed crawler entrypoints to rely on the
  prepared environment, verify TLS by default, accept output/query arguments,
  check GraphQL errors, filter empty abstracts, and return non-zero on failure.
- Verification: `python -m py_compile src/crawler/api_fetcher.py
  src/crawler/pubmed_crawler.py src/crawler/topic_clustering.py
  src/crawler/topic_balanced_pubmed.py` passed; source scan no longer finds
  `verify=False` or `subprocess.check_call` in `src/crawler`.

### 2026-06-09 - Hardened script entrypoints could not import `src`

- Symptom: Running new scripts directly with commands such as
  `python src/extraction/local_pipeline.py` failed with
  `ModuleNotFoundError: No module named 'src'`.
- Cause: Python placed the script directory on `sys.path`, but not reliably the
  repository root where the namespace package `src` is resolved.
- Fix: Added a small repository-root `sys.path` guard to script entrypoints that
  import shared `src.*` modules.
- Verification: `python -m py_compile` passed for the updated crawler,
  extraction, fusion, and database scripts; Stage 2 local-rule and gold-candidate
  probes ran successfully afterward.

### 2026-06-09 - HuggingFace endpoint was set too late for medical alignment

- Symptom: Stage 3 fusion probe attempted to load
  `NeuML/pubmedbert-base-embeddings` through `huggingface.co` and failed with an
  SSL/client error, then fell back to dictionary-only alignment.
- Cause: `HF_ENDPOINT` was set inside `main()` after importing
  `sentence_transformers`, so HuggingFace client configuration could already be
  initialized.
- Fix: Set the default `HF_ENDPOINT` before importing `sentence_transformers` in
  the Stage 3 semantic aligner and Stage 1 topic clustering runner.
- Verification: `python -m py_compile src/fusion/semantic_aligner.py
  src/crawler/topic_clustering.py` passed, and unit tests still pass.

### 2026-06-09 - Stage 4 analytics community IDs were non-deterministic

- Symptom: Two Stage 4 local reruns with identical `fused_triples.jsonl` and
  Open Targets inputs produced different `analytics_metrics.csv` and
  `graph_viewer.html` hashes. PageRank values were stable, but 516 of 607 nodes
  changed `Community_ID`.
- Cause: `graph_analytics.py` called
  `nx.community.louvain_communities()` without a fixed seed, then assigned
  community IDs from unordered community/node iteration.
- Fix: Added a fixed community seed, sorted communities and community members by
  node name, and sorted analytics output by `PageRank` then `Entity`.
- Verification: `artifacts/runs/stage4_graph_database_2026-06-09/` contains two
  fixed-seed reruns with identical hashes:
  `analytics_metrics_fixed_first.csv` and `analytics_metrics_fixed_second.csv`
  both hash to
  `3e3f8c1653a19cd5adcc303664b4a528b37e20dbf798f19a3a5cd668b9ce3116`;
  `graph_viewer_fixed_first.html` and `graph_viewer_fixed_second.html` both
  hash to
  `fe93189804ef2a982bb6c16147c8266e139fe3bc1a90407c6734284bd1d050d0`.

### 2026-06-09 - Stage 3 outputs were stale after stabilized Stage 2

- Symptom: Stage 3 fusion outputs still reflected the older 2664-triple Stage 2
  input, while the stabilized Stage 2 canonical input now contained 5738 merged
  triples.
- Cause: `dictionary_mapper.py`, `semantic_aligner.py`, and
  `triples_aggregator.py` write directly to canonical output paths and had not
  been rerun after the Stage 2 promotion.
- Fix: Reran the Stage 3 scripts, captured pre-run snapshots, logs, output
  snapshots, a manifest, and validation statistics under
  `artifacts/runs/stage3_fusion_2026-06-09/`.
- Verification: Stage 3 now reports 5738 mapped triples, 5738 aligned triples,
  and 554 fused unique edges. A Stage 4 dry-read of
  `data/processed/fused_triples.jsonl` loaded all 554 records with 0 missing core
  fields.

### 2026-06-09 - Stage 2 full extraction needed recoverable execution

- Symptom: Stage 2 LLM extraction was too slow and fragile as one monolithic
  200-record run. Earlier attempts could be interrupted and either leave partial
  `.tmp` data or risk stale/historical LLM outputs being mixed with fresh Regex
  output.
- Cause: The original Stage 2 flow had no chunk manifest, no resumable runner,
  no validation gate, and no promote-only-after-validation step.
- Fix: Added `src/extraction/run_stage2_extraction.py` to generate a fixed
  Stage 2 split, run DeepSeek V4 Flash in 20-PMID chunks, resume valid chunks,
  validate LLM/Regex/merged JSONL outputs, write run artifacts, and promote only
  after validation passes.
- Verification: `python src/extraction/run_stage2_extraction.py --run-dir artifacts/runs/stage2_extraction_full_2026-06-08_2335 --llm-limit 200 --chunk-size 20 --model deepseek-ai/DeepSeek-V4-Flash --max-tokens 2048 --promote` completed successfully. Validation reports 638 LLM triples, 5101 Regex triples, and 5738 merged triples with 0 bad JSON lines and 0 invalid triples; a Stage 3 dictionary-mapper dry-read loaded all 5738 merged triples without code changes.

### 2026-06-08 - Stage 2 LLM extraction could not be faithfully rerun

- Symptom: The second-stage LLM extractor could not be safely rerun because
  `SILICONFLOW_API_KEY` was missing. The local regex extractor and merge step
  could run, but the merged output would combine historical LLM triples with
  newly reproduced regex triples.
- Cause: `llm_extractor.py` requires a live SiliconFlow key, hard-codes the
  first 200 abstracts and output path, and has no dry-run, fixture, small-sample,
  or alternate-output mode. Running it without a key would trigger repeated
  failures and risk overwriting the historical LLM output.
- Fix: Preserved pre-run stage-2 outputs under
  `artifacts/runs/stage2_extraction_2026-06-08/pre_run_outputs/`, reran only
  the reproducible local regex and merge steps, wrote logs and a manifest under
  `artifacts/runs/stage2_extraction_2026-06-08/`, and documented the partial
  reproduction boundary.
- Verification: `manifest.csv` reports 674 historical LLM triples, 5101 rerun
  regex triples, and 5775 merged triples, each with 0 invalid JSON lines.

### 2026-06-08 - Stage 1 rerun outputs were not auditable

- Symptom: First-stage crawler reruns wrote directly to `data/external/` and
  `data/raw/`, overwriting canonical data without a dated run directory,
  manifest, log capture, or output snapshot.
- Cause: The crawler scripts use hard-coded output paths and do not generate run
  metadata. Historical loose outputs made it hard to tell which artifacts came
  from which run.
- Fix: Reran the stage with logs captured under
  `artifacts/runs/stage1_data_acquisition_2026-06-08/`, copied the reproduced
  outputs into that dated run directory, generated `manifest.csv`, and documented
  the convention in `artifacts/README.md`.
- Verification: `manifest.csv` reports 164 valid Open Targets JSONL rows and
  4555 valid PubMed JSONL rows with 0 invalid JSON lines.

### 2026-06-06 - Consolidated conda environment

- Symptom: The repository had multiple candidate conda environments (`kg_sma`,
  `kg_env`, and `base`) with inconsistent dependency coverage.
- Cause: `kg_sma` and `kg_env` were not aligned with the packages required by
  `requirements.txt` and observed imports in `src/`.
- Fix: Removed `kg_sma` and `kg_env`, then cloned `base` into `KG_SMA_env`.
- Verification: `KG_SMA_env` reports Python 3.13.5 and successfully imports
  `requests`, `urllib3`, `pandas`, `Bio`, `bertopic`, `sklearn`, `jupyter`,
  `ipykernel`, `tqdm`, `tenacity`, `openai`, `neo4j`, `sentence_transformers`,
  `pyvis`, `networkx`, `thefuzz`, and `numpy`.
