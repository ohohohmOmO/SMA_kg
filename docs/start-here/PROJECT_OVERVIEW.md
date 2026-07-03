# SMA Knowledge Graph

This repository builds a biomedical knowledge graph for Spinal Muscular Atrophy
(SMA). The current implementation collects SMA data from Open Targets and
PubMed, extracts relation triples from literature, fuses synonymous entities,
computes graph metrics, generates an HTML graph viewer, and evaluates extraction
quality.

## Start Here

- Required reading index: `docs/start-here/README.md`
- Agent and contributor rules: `docs/start-here/AGENT_GUIDE.md`
- Run checklist: `docs/start-here/PLAN.md`
- Issue log: `docs/start-here/ISSUE_LOG.md`
- Domain glossary: `docs/start-here/CONTEXT.md`
- Latest handoff: `docs/start-here/PROJECT_HANDOFF_2026-06-09.md`
- Current hardening notes: `docs/reproduction/ENGINEERING_HARDENING_2026-06-09.md`
- Stage 3 preparation status: `docs/reproduction/STAGE3_PREP_2026-06-09.md`
- Pre-improvement baseline: `results/runs/pre_improvement_baseline_2026-06-09/manifest.csv`
- Archived old overview: `docs/archive/SMA_KG_Project_Overview_OLD.md`

Use the latest handoff for project onboarding. Older handoff snapshots have
been removed so `docs/start-here/PROJECT_HANDOFF_2026-06-09.md` is the source of truth.

## Environment

Use the conda environment prepared for this repository:

```powershell
conda activate KG_SMA_env
python --version
python -m pip install -r requirements.txt
```

Store local secrets in `.env` or `.env.local` by copying `.env.example`. Real
secret files are ignored by git and must not be committed.

External services and environment variables:

- `SILICONFLOW_API_KEY` for LLM extraction and LLM-based evaluation.
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for Neo4j import and topology
  checks.
- `HF_ENDPOINT`, commonly `https://hf-mirror.com`, for HuggingFace model access.

## Repository Layout

```text
src/
  crawler/        Open Targets and PubMed acquisition
  biomedical/     shared schema, confidence, and evidence alignment
  evidence/       local Evidence Context builders for RAG and adjudication
  extraction/     LLM extraction, rule candidates, verification, merge step
  fusion/         dictionary mapping, semantic alignment, triple aggregation
  qa/             local Graph RAG retrieval and answer generation CLIs
  database/       Neo4j import, NetworkX analytics, PyVis graph export
  evaluation/     baseline evaluation, human/LLM scoring, novelty analysis
tests/            unit tests and external-service smoke tests
notebooks/        BERTopic exploration and topic visualization
resources/        Biomedical schema and entity dictionary resources
data/
  raw/            PubMed abstracts
  external/       Open Targets baseline data
  interim/        mapped and aligned intermediate triples
  processed/      canonical outputs consumed by later stages
results/
  runs/           dated manifests, logs, snapshots, and validation summaries
  reports/        archived evaluation and command reports
  test-results/   generated smoke-test outputs
  visualizations/ graph viewer and its local browser libraries
docs/
  start-here/     required current context and operating rules
  design/         technical plans and roadmaps
  reproduction/   reproducible implementation and run records
  archive/        historical documents
```

## Pipeline

Run from the repository root.

```powershell
python src/crawler/api_fetcher.py
python src/crawler/pubmed_crawler.py
python src/crawler/topic_clustering.py
python src/crawler/topic_balanced_pubmed.py --topic-terms-file <topic_terms.json>

python src/extraction/run_stage2_extraction.py --run-dir results/runs/stage2_extraction_<stamp> --llm-limit -1 --chunk-size 5 --parallel-workers 32 --promote
python src/extraction/validate_evidence_spans.py --run-dir results/runs/evidence_span_audit_<stamp>
python src/extraction/verify_rule_candidates.py --input-file data/interim/rule_candidate_triples.jsonl --limit 50
python src/extraction/build_gold_candidates.py --run-dir results/runs/stage2_gold_candidates_<stamp> --limit 750

python src/fusion/run_stage3_fusion.py --run-dir results/runs/stage3_fusion_<stamp> --promote
python src/fusion/adjudicate_relation_conflicts.py --dry-run --run-dir results/runs/conflict_adjudication_dry_run_<stamp>

python src/database/run_stage4_graph.py --run-dir results/runs/stage4_graph_database_<stamp>

python src/evaluation/baseline_eval_advanced.py
python src/evaluation/ablation_study.py
python src/evaluation/novelty_analysis.py

python src/qa/build_index.py --retrieval-mode hybrid_tfidf --run-dir results/runs/graph_rag_index_<stamp>
python src/qa/run_graph_rag.py --question "What evidence links SMN1 to spinal muscular atrophy?" --retrieval-mode hybrid_tfidf --dry-run --output-file results/runs/graph_rag_answer_probe_<stamp>/answer_dry_run.json
python src/qa/run_graph_rag.py --question "Which genes are strongly connected to Spinal Muscular Atrophy?" --retrieval-mode hybrid_tfidf --include-neo4j-neighborhood --dry-run
python src/fusion/prepare_conflict_adjudication_review.py --adjudications-file results/runs/conflict_adjudication_live_<stamp>/adjudications.jsonl --run-dir results/runs/conflict_adjudication_review_<stamp>
```

Optional steps that require external services:

```powershell
python src/database/neo4j_importer.py
python src/evaluation/topology_eval.py
python src/evaluation/metrics_calculator.py
python src/fusion/adjudicate_relation_conflicts.py --run-dir results/runs/conflict_adjudication_live_<stamp>
python src/qa/run_graph_rag.py --question "How does Nusinersen affect motor function?"
```

## Current Outputs

- `data/raw/pubmed_sma_abstracts.jsonl`: PubMed SMA abstracts.
- `data/processed/clustered_abstracts.jsonl`: Stage 1 topic clustering output.
- `data/external/sma_gda_baseline.jsonl`: Open Targets gene-disease baseline.
- `data/processed/llm_extracted_triples.jsonl`: validated LLM extraction output.
- `data/processed/extracted_triples.jsonl`: Stage 2 canonical LLM-only output.
- `data/interim/rule_candidate_triples.jsonl`: local rule candidates for review,
  recall analysis, gold-standard sampling, and ablation.
- `data/interim/verified_rule_triples.jsonl`: optional LLM/human-verified rule
  candidates; not promoted automatically.
- `data/interim/mapped_triples.jsonl`: dictionary-normalized triples.
- `data/interim/aligned_triples.jsonl`: semantically aligned triples.
- `data/processed/fused_triples.jsonl`: fused unique graph edges.
- `data/interim/relation_conflicts.jsonl`: Stage 3 relation polarity conflicts
  requiring review.
- `data/interim/aggregation_rejected.jsonl`: Stage 3 rejected aggregation
  records.
- `data/processed/graph_rag_index_manifest.json`: local Graph RAG input
  manifest with source counts and hashes.
- `data/processed/analytics_metrics.csv`: PageRank and community metrics.
- `results/visualizations/graph_viewer.html`: generated interactive graph viewer.
- `results/reports/`: archived historical command outputs and evaluation
  reports.

As of 2026-06-09, Stage 1 acquisition/topic clustering, Stage 2 full LLM-only
extraction, Stage 3 fusion/alignment/conflict detection, and Stage 4 Neo4j plus
local graph generation have been rerun successfully. Current Stage 3/4 results
are recorded in `docs/reproduction/STAGE3_STAGE4_REPRO_2026-06-09.md`.

As of 2026-06-10, Graph RAG retrieval and relation-conflict adjudication v1 are
implemented as local-retrieval-first CLIs. Local retrieval builds bounded
Evidence Context packages from canonical JSONL files; LLM calls are optional and
consume only that evidence. Retrieval supports lexical/entity mode,
`hybrid_tfidf` reranking, and optional read-only Neo4j neighborhood expansion.
Conflict adjudication outputs must be converted into human-review proposals
before any graph promotion. Reproduction details are recorded in
`docs/reproduction/GRAPH_RAG_CONFLICT_ADJUDICATION_2026-06-10.md`.

As of 2026-07-03, Graph RAG answers use a locally enforced hard-citation
contract. Claims must reference allowlisted PMIDs and stable Evidence Context
IDs, PMID/evidence mismatches are rejected, invalid generations receive bounded
correction attempts, and exhausted validation returns a safe answer without
unvalidated claims. Reproduction details are recorded in
`docs/reproduction/GRAPH_RAG_HARD_CITATION_VALIDATION_2026-07-03.md`.

Also as of 2026-07-03, new Stage 2 LLM triples must align `evidence_text` to
their PMID-linked abstract before they can pass the promotion gate. Alignment
uses exact, punctuation/spacing-normalized, and conservative local fuzzy
matching with source character offsets. A read-only audit of the current 18288
canonical triples aligned 16214 records and isolated 2074 for review without
changing canonical data. Reproduction details are recorded in
`docs/reproduction/EVIDENCE_SPAN_VALIDATION_2026-07-03.md`.

Open decisions before changing Stage 1 or Stage 2 inputs:

- `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`
- `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`

See `docs/start-here/PROJECT_HANDOFF_2026-06-09.md` for the current project handoff.
