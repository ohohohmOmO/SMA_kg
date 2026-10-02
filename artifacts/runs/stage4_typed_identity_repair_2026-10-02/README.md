# Stage 4 Graph And Neo4j Run

- Valid: False
- Neo4j status: `ok`
- Neo4j TCP: `localhost:7687`
- Input file: `data/processed/fused_triples.jsonl`
- Input SHA-256: `ecdd5e68a308309f423b5ade455d14131152f67dcf978579c9f254c9d7de0e5d`
- Promoted: False
- Preserve Neo4j: False

## Outputs

- analytics_metrics: `artifacts\runs\stage4_typed_identity_repair_2026-10-02\outputs\data\processed\analytics_metrics.csv`
- graph_viewer: `artifacts\runs\stage4_typed_identity_repair_2026-10-02\outputs\docs\graph_viewer.html`
- neo4j_import_summary: `artifacts\runs\stage4_typed_identity_repair_2026-10-02\outputs\database\neo4j_import_summary.json`
- topology_metrics: `artifacts\runs\stage4_typed_identity_repair_2026-10-02\outputs\evaluation\topology_metrics.json`

## Commands

- neo4j_import: exit_code=0, log=`artifacts\runs\stage4_typed_identity_repair_2026-10-02\logs\neo4j_import.log`
- topology_eval: exit_code=0, log=`artifacts\runs\stage4_typed_identity_repair_2026-10-02\logs\topology_eval.log`
- graph_analytics: exit_code=0, log=`artifacts\runs\stage4_typed_identity_repair_2026-10-02\logs\graph_analytics.log`
- generate_pyvis: exit_code=1, log=`artifacts\runs\stage4_typed_identity_repair_2026-10-02\logs\generate_pyvis.log`
