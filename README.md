# SMA Knowledge Graph & Digital Twin

## 📖 Introduction
This project aims to construct a high-density, high-quality Knowledge Graph (KG) for **Spinal Muscular Atrophy (SMA)**. It systematically integrates data regarding SMA-associated genes (e.g., SMN1, SMN2), pathogenic mechanisms, clinical phenotypes, and drug treatments. This KG serves as the core logic engine and data foundation for an SMA Digital Twin system.

The project emphasizes a fully automated, zero-human-annotation pipeline, utilizing Large Language Models (LLMs) for relation extraction, small Sentence-Transformer models for semantic fusion, and Neo4j for persistent graph storage.

## 🛠️ Technology Stack
* **Language:** Python 3.x
* **Data Sources:** Open Targets API (GraphQL), PubMed Literature
* **NLP & AI:**
  * **LLM Engine:** Qwen2.5-7B-Instruct (via SiliconFlow API) for Named Entity Recognition (NER) and Relation Extraction (RE).
  * **Semantic Alignment:** HuggingFace `sentence-transformers` (`all-MiniLM-L6-v2`), `scikit-learn` (Cosine Similarity).
  * **Topic Clustering:** `BERTopic`
* **Graph Database:** Neo4j (Cypher query language)
* **Visualization:** PyVis, ECharts, HTML exports
* **Data Processing:** `pandas`, `requests`, `tenacity` (for retry logic), JSONL formatted intermediate files.

## 📂 Repository Structure

```text
kg_sma_0420/
├── data/                  # Pipeline Data IO (raw, processed, interim, external)
├── docs/                  # Project specifications and historical technical plans
├── lib/                   # Project specific libraries and modules
├── notebooks/             # Data exploration, clustering (BERTopic), and visualizations
├── src/                   # Core pipeline source code
│   ├── crawler/           # Phase 1: Data Acquisition (PubMed, Open Targets)
│   ├── extraction/        # Phase 2: Knowledge Extraction (LLM / NLP)
│   ├── fusion/            # Phase 3: Semantic Alignment & Deduplication
│   ├── database/          # Phase 4: Neo4j Import & Graph Analytics
│   └── evaluation/        # Phase 5: Relation-level Metrics, Ablation & Novelty Search
├── requirements.txt       # Python dependencies
├── final_reports.txt      # Evaluation reports (baseline, ablation, novelty discovery)
└── test_ot.py             # Script for testing OpenTargets API integration
```

## 🚀 Key Pipeline Phases

1. **Phase 1: Data Acquisition (`src/crawler/`)**
   - Interacts with Open Targets GraphQL API and crawls PubMed abstracts based on SMA-related keywords.
2. **Phase 2: Knowledge Extraction (`src/extraction/`)**
   - Uses Qwen2.5-7B via SiliconFlow API to extract biomedical triples (`Gene`, `Protein`, `Phenotype`, `Drug`).
3. **Phase 3: Semantic Fusion & Alignment (`src/fusion/`)**
   - Loads `all-MiniLM-L6-v2` transformer model to generate entity embeddings and clusters them to remove redundant synonyms.
4. **Phase 4: Database & Graph Computation (`src/database/`)**
   - Ingests triples into Neo4j using Cypher MERGE queries. Calculates graph topology metrics like PageRank and Community Detection.
5. **Phase 5: Evaluation & Novelty Discovery (`src/evaluation/`)**
   - Evaluates extraction and performs ablation studies on semantic fusion (metrics can be found in `final_reports.txt`).

## ⚙️ Environment Configuration

Set the following environment variables to run the pipeline:
* `SILICONFLOW_API_KEY`: Required for LLM extraction and evaluation (Phase 2 & 5).
* `NEO4J_URI`: e.g., `bolt://localhost:7687`
* `NEO4J_USER`: e.g., `neo4j`
* `NEO4J_PASSWORD`: Neo4j password
* `HF_ENDPOINT`: Typically set to `https://hf-mirror.com` (to bypass region blocks when downloading HuggingFace models).

## 🏃 Getting Started
1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute the data pipeline sequentially via the scripts in the `src/` directory. Check `data/` directory for input/output files.

## 📊 Project Results
The latest ablation studies and novelty discovery outcomes are documented in `final_reports.txt`. The pipeline effectively enhances graph density and isolates potential new discoveries through automated analysis.
