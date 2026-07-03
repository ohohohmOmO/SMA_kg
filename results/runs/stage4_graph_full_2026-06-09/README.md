# Stage 4 Graph And Neo4j Run

- Valid: True
- Neo4j status: `ok`
- Neo4j TCP: `localhost:7687`
- Input file: `data\processed\fused_triples.jsonl`
- Input SHA-256: `1771293aad8258befe717c7c7ca00c349fe5fdb782b84245b1357ad45e332b5a`
- Promoted: True
- Preserve Neo4j: False

## Outputs

- analytics_metrics: `artifacts\runs\stage4_graph_full_2026-06-09\outputs\data\processed\analytics_metrics.csv`
- graph_viewer: `artifacts\runs\stage4_graph_full_2026-06-09\outputs\docs\graph_viewer.html`
- neo4j_import_summary: `artifacts\runs\stage4_graph_full_2026-06-09\outputs\database\neo4j_import_summary.json`
- topology_metrics: `artifacts\runs\stage4_graph_full_2026-06-09\outputs\evaluation\topology_metrics.json`

## Commands

- neo4j_import: exit_code=0, log=`artifacts\runs\stage4_graph_full_2026-06-09\logs\neo4j_import.log`
- topology_eval: exit_code=0, log=`artifacts\runs\stage4_graph_full_2026-06-09\logs\topology_eval.log`
- graph_analytics: exit_code=0, log=`artifacts\runs\stage4_graph_full_2026-06-09\logs\graph_analytics.log`
- generate_pyvis: exit_code=0, log=`artifacts\runs\stage4_graph_full_2026-06-09\logs\generate_pyvis.log`
