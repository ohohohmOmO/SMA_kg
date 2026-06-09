# OLD: SMA Knowledge Graph & Digital Twin - Project Overview

This is an archived overview. It is retained for historical context only.
For the current repository handoff, see
`docs/PROJECT_HANDOFF_2026-06-09.md`. For current onboarding, start with
`README.md`, `AGENTS.md`, and `docs/agents/PLAN.md`.

## 1. Project Goal & Scope
This project aims to construct a high-density, high-quality Knowledge Graph (KG) for **Spinal Muscular Atrophy (SMA)**. It systematically integrates data regarding SMA-associated genes (e.g., SMN1, SMN2), pathogenic mechanisms, clinical phenotypes, and drug treatments. This KG serves as the core logic engine and data foundation for an SMA Digital Twin system.

The project emphasizes a fully automated, zero-human-annotation pipeline, utilizing Large Language Models (LLMs) for relation extraction, small Sentence-Transformer models for semantic fusion, and Neo4j for persistent graph storage.

## 2. Technology Stack
* **Language:** Python 3.x
* **Data Sources:** Open Targets API (GraphQL), PubMed Literature
* **NLP & AI:**
  * **LLM Engine:** Qwen2.5-7B-Instruct (via SiliconFlow API) for Named Entity Recognition (NER) and Relation Extraction (RE).
  * **Semantic Alignment:** HuggingFace `sentence-transformers` (`all-MiniLM-L6-v2`), `scikit-learn` (Cosine Similarity).
  * **Topic Clustering:** `BERTopic`
* **Graph Database:** Neo4j (Cypher query language)
* **Visualization:** PyVis, ECharts, HTML exports
* **Data Processing:** `pandas`, `requests`, `tenacity` (for retry logic), JSONL formatted intermediate files.

## 3. Repository Structure Map

```text
kg_sma_0420/
├── data/                  # Pipeline Data IO (Crucial for testing/debugging)
│   ├── raw/               # Raw scraped literature/abstracts (e.g. pubmed_sma_abstracts.jsonl)
│   ├── processed/         # Formatted triples, scored evaluation data (e.g. llm_extracted_triples.jsonl)
│   ├── interim/           # Intermediate mapping data for fusion pipelines
│   └── external/          # Baseline datasets from external APIs (e.g. sma_gda_baseline.jsonl)
├── docs/                  # Project specifications and historical technical plans
│   └── SMA_KG_Technical_Plan.md
├── notebooks/             # Data exploration, clustering (BERTopic), and visualizations
├── src/                   # Core pipeline source code
│   ├── crawler/           # Phase 1: Data Acquisition
│   ├── extraction/        # Phase 2: Knowledge Extraction (LLM / NLP)
│   ├── fusion/            # Phase 3: Semantic Alignment & Deduplication
│   ├── database/          # Phase 4: Neo4j Import & Graph Analytics
│   └── evaluation/        # Phase 5: Relation-level Metrics, Ablation & Novelty Search
├── requirements.txt       # Python dependencies
└── ... (logs and testing scripts)
```

## 4. Key Modules & Pipeline Flow

The system is designed as a multi-phase pipeline. AI Agents should understand the inputs and outputs of each module.

### Phase 1: Data Acquisition (`src/crawler/`)
* **`api_fetcher.py`**: Interacts with the Open Targets GraphQL API (`https://api.platform.opentargets.org/api/v4/graphql`) to establish baseline Gene-Disease Associations (GDAs) for SMA (`MONDO_0009669` or `EFO_0000109`). Outputs baseline triples to `data/external/`.
* **`pubmed_crawler.py`**: Fetches abstracts from PubMed using SMA-related keywords to expand the knowledge base.

### Phase 2: Knowledge Extraction (`src/extraction/`)
* **`llm_extractor.py`**: Reads raw abstracts. Calls Qwen2.5-7B via SiliconFlow API to extract biomedical triples (Entity 1, Relation, Entity 2). Focuses strictly on `Gene`, `Protein`, `Phenotype`, and `Drug` entities. Outputs standardized JSON formats to `data/processed/llm_extracted_triples.jsonl`.
* **`local_pipeline.py` & `merge_triples.py`**: Support local models (like UIE-med or BioBERT) for large-scale extraction and merging results.

### Phase 3: Semantic Fusion & Alignment (`src/fusion/`)
* **`semantic_aligner.py`**: Solves the problem of synonym redundancy. It loads the `all-MiniLM-L6-v2` transformer model to generate entity embeddings and clusters them using Cosine Similarity (threshold `0.88`). Finds canonical names based on frequency and aligns triples accordingly. Outputs to `data/interim/aligned_triples.jsonl`.
* **`dictionary_mapper.py` & `triples_aggregator.py`**: Handle deterministic dictionary mapping and resolution of relation conflicts via confidence scores and frequency.

### Phase 4: Database & Graph Computation (`src/database/`)
* **`neo4j_importer.py`**: Connects to the local/remote Neo4j instance. Enforces node uniqueness constraints (`Entity.name`). Ingests both Open Targets baseline and the fused literature triples using dynamic Cypher MERGE queries.
* **`graph_analytics.py` & `generate_pyvis.py`**: Calculate graph topology (PageRank, Community Detection) and generate interactive HTML visualizations.

### Phase 5: Evaluation & Novelty Discovery (`src/evaluation/`)
* **`metrics_calculator.py`**: Implements LLM-as-a-judge to evaluate the factuality of extracted triples against human scores. Calculates `Cohen's Kappa`, strict (2) and lenient (1) accuracies.
* **`ablation_study.py` & `novelty_analysis.py`**: Automates evaluation experiments to measure the impact of fusion. The novelty analysis pipeline helps discover new scientific findings (triples) not yet present in standard baseline databases.

## 5. Configuration & Environment Variables
To successfully run or test scripts in this repository, the following environment variables are required:
* `SILICONFLOW_API_KEY`: Required for Phase 2 extraction and Phase 5 LLM evaluation using Qwen models.
* `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Required for Phase 4 to connect to the graph database (defaults to `bolt://localhost:7687`, `neo4j`, `password`).
* `HF_ENDPOINT`: Typically set to `https://hf-mirror.com` in scripts (like `semantic_aligner.py`) to bypass region blocks when downloading HuggingFace models.

## 6. Guidelines for AI Agents (Developers & Testers)

1. **Dependency Management**: Ensure you run `pip install -r requirements.txt` before executing tasks. Some scripts (e.g. `api_fetcher.py`, `semantic_aligner.py`) contain inline auto-install snippets, but installing via requirements is safer.
2. **Data Mocking for Tests**: If testing the pipeline, use small subsets of JSONL files (e.g., `head -n 100`) in `data/raw/` to avoid massive API costs or long LLM processing times.
3. **Cypher Queries**: When modifying `src/database/neo4j_importer.py`, ensure Cypher queries remain injection-safe by using parameters (`$variable_name`) rather than f-string injections for values. Note that node labels / relation types still require string interpolation but must be carefully sanitized.
4. **Resiliency**: Network calls heavily utilize the `tenacity` library for exponential backoff. Always wrap new API/LLM calls with `@retry` decorators.
5. **Output Standardization**: Any newly generated evaluation or triple datasets must strictly follow the JSON Lines format (`.jsonl`) to ensure compatibility with downstream aggregator scripts.
