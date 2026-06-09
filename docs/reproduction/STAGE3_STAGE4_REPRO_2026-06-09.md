# Stage 3 And Stage 4 Full Rerun - 2026-06-09

This document records the completed Stage 3 fusion/alignment rerun and Stage 4
Neo4j/database graph rerun after the full-corpus Stage 2 LLM-only extraction.

## Inputs

- Stage 2 canonical triples: `data/processed/extracted_triples.jsonl`
- Stage 2 canonical records: 18288
- Stage 2 canonical SHA-256:
  `0d23d5dd162744dd70228905e6367800658e5d0af0b7328df50a6e62bfde76cb`
- Open Targets baseline: `data/external/sma_gda_baseline.jsonl`
- Open Targets SHA-256:
  `f02cb91fb0e6e75debcd549b615aadb6d7a50965cd9ea3bff3eebb13444b76cb`

## Stage 3 Command

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src\fusion\run_stage3_fusion.py --run-dir artifacts\runs\stage3_fusion_full_2026-06-09 --alignment-model NeuML/pubmedbert-base-embeddings --promote
```

## Stage 3 Implementation Notes

- Entity dictionary normalization loads from
  `resources/entity_dictionary.json`.
- Relation aliases and relation polarity load from
  `resources/biomedical_schema.json`.
- Semantic alignment used `NeuML/pubmedbert-base-embeddings`.
- The aligner computed embeddings by entity type and used deterministic
  connected components over the similarity graph.
- Aggregation used component-based fused confidence scoring.
- Relation conflict detection marks positive/negative polarity conflicts as
  `needs_review` and writes them to a separate conflict file.

## Stage 3 Results

| Output | Records | Bad JSON | Invalid triples | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `data/interim/mapped_triples.jsonl` | 18288 | 0 | 0 | `7f10841e68bcd54aeb58658562e1147b20c5a4502b8ef5928ef08c7637b9e4f8` |
| `data/interim/aligned_triples.jsonl` | 18288 | 0 | 0 | `65fc3e961e37e5361b47dd46dccef4916575d0e3b71130a8e6c775a18b36e58e` |
| `data/processed/fused_triples.jsonl` | 11155 | 0 | 0 | `1771293aad8258befe717c7c7ca00c349fe5fdb782b84245b1357ad45e332b5a` |
| `data/interim/relation_conflicts.jsonl` | 59 | 0 | 0 | `96c8923c9d67776b00936169323ee092979870d40b15c5a932d37a022b2924db` |
| `data/interim/aggregation_rejected.jsonl` | 0 | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Additional Stage 3 facts:

- 164 fused records have `review_status=needs_review`.
- 59 entity pairs have relation polarity conflicts.
- Stage 3 promotion succeeded.
- Run directory:
  `artifacts/runs/stage3_fusion_full_2026-06-09/`

## Stage 4 Command

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src\database\run_stage4_graph.py --run-dir artifacts\runs\stage4_graph_full_2026-06-09 --input-file data\processed\fused_triples.jsonl --opentargets-file data\external\sma_gda_baseline.jsonl --promote
```

## Stage 4 Implementation Notes

- `src/database/run_stage4_graph.py` now writes all outputs to a run directory
  before promotion.
- The runner loads ignored local `.env` and `.env.local` files for Neo4j
  credentials.
- Neo4j service reachability is checked over TCP before import.
- The Neo4j importer verifies driver connectivity before importing.
- Dynamic labels and relationship types are restricted through the biomedical
  schema before Cypher construction.
- The default Stage 4 run clears previously managed SMA KG relationships and
  managed/orphan `Entity` nodes before importing the latest graph. Use
  `--preserve-neo4j` only when intentionally accumulating graph state.
- `topology_eval.py` writes JSON metrics into the run directory.
- NetworkX analytics and PyVis graph viewer are generated from the Stage 3
  fused file and promoted only after validation passes.

## Stage 4 Results

- Run directory:
  `artifacts/runs/stage4_graph_full_2026-06-09/`
- Neo4j status: `ok`
- Neo4j TCP check: `localhost:7687`
- Cleared managed relationships: 11208
- Cleared managed/orphan `Entity` nodes: 6648
- Imported Open Targets relationships: 164
- Imported fused literature triples: 11155
- Neo4j total nodes: 6648
- Neo4j total relationships: 11208
- Neo4j average node degree: 3.371841155234657
- Neo4j isolated node ratio: 0.0
- Local analytics records: 6648
- Graph viewer bytes: 4149758
- Stage 4 promotion succeeded.

Promoted canonical outputs:

- `data/processed/analytics_metrics.csv`
- `docs/graph_viewer.html`

Archived Stage 4 outputs:

- `artifacts/runs/stage4_graph_full_2026-06-09/outputs/data/processed/analytics_metrics.csv`
- `artifacts/runs/stage4_graph_full_2026-06-09/outputs/docs/graph_viewer.html`
- `artifacts/runs/stage4_graph_full_2026-06-09/outputs/database/neo4j_import_summary.json`
- `artifacts/runs/stage4_graph_full_2026-06-09/outputs/evaluation/topology_metrics.json`

## Verification

Focused checks:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m py_compile src\fusion\run_stage3_fusion.py src\fusion\dictionary_mapper.py src\fusion\semantic_aligner.py src\fusion\triples_aggregator.py src\database\run_stage4_graph.py src\database\neo4j_importer.py src\database\graph_analytics.py src\database\generate_pyvis.py src\evaluation\topology_eval.py tests\unit\test_biomedical_quality.py
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' -m unittest discover -s tests/unit -v
```

Result: compile passed; 10 unit tests passed.

## Remaining Open Decisions

These decisions remain tracked and do not block the completed Stage 3/4 rerun:

- `.scratch/stage3-prep/issues/01-review-topic-balanced-expansion.md`
- `.scratch/stage3-prep/issues/02-build-gold-set-before-medical-model-finetuning.md`
