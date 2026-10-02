# FYP four repairs reproduction and acceptance

Use `KG_SMA_env` from the repository root; read `docs/agents/PLAN.md` first.
The latest delivery is `artifacts/runs/fyp_four_repairs_final_2026-10-02/`.
Earlier dated runs are retained historical evidence, including a failed Windows
PyVis export and the original sentence-context experiment.

## Inputs and sequential stages

1. `stage3_identity_repair_2026-10-02`: frozen 18,288 raw rows; typed dictionary
   guards and conservative orthographic identity; 13,001 edges, 36 conflict
   pairs, two self-loops. `identity_validation.json` and
   `smn2_restoration_records.jsonl` verify all 982 erroneous endpoints/618 PMIDs.
   `promotion.json` records hashes and backups of old canonical files.
2. `assertion_quality_repair_2026-10-02`: protocol frozen before 400 model calls,
   temperature 0, DeepSeek V4 Flash, eight workers, 1,400 output tokens. Human
   labels/notes excluded from requests. All replies retained; no rewrites.
3. `assertion_quality_context_fixed_2026-10-02`: documented decimal-boundary
   correction; replays unchanged requests/replies without new API calls.
   `replay_provenance.json` records original decisions hash and correction.
   Final full-corpus triage: 16,724 needs_review and 1,564 screened_candidate;
   neither status means human-verified truth. 108 quote/schema failures fail closed.
4. `fyp_four_repairs_final_2026-10-02`: fresh controlled fusion, human statistics,
   results chapter/figures/error cases, offline evidence and complete graph.
5. Versioned typed Neo4j import is activated only after full property
   reconciliation. Current acceptance version `typed-v2-8a4dbccd4fdc22ca`;
   9,218 nodes, 13,001 literature +164 external relationships, all 18,288 original
   evidence records. Legacy Entity counts remain 6,648/11,208. Intermediate
   typed version `typed-v2-fe93797a156149f5` is also preserved, and its repeated
   import established idempotence before the context correction.
6. `stage4_typed_identity_repair_2026-10-02` records successful DB import and
   topology/analytics but failed GBK PyVis output; `stage4_typed_identity_repair_verified_2026-10-02`
   records successful focused UTF-8 local rerun. Canonical analytics uses
   MultiDiGraph typed/source identity; parallel relation types are retained.
7. `fyp_scope_revision_2026-10-02` preserves five original Word drafts, reviewed
   replacements, hashes and source promotion. Final pages 5/4/2/4/8; all23 pages
   visually checked. Preliminary report meets 8 pages, 4 technical-background
   pages, 1 work-plan page. Original Word formatting preserved; ethics summary
   shortened to keep both signature rows on page2. Missing packaged pdf2image/
   LibreOffice was diagnosed; hidden installed Word COM exported PDFs and bundled
   Poppler produced page images. Temporary QA images are not deliverables.

## Reproduction commands

Use fresh run paths. Do not overwrite completed runs or invoke clearing.
The model replay requires the preserved original run; it makes no new calls.

```powershell
$pythonSma = 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe'
& $pythonSma src/fusion/run_stage3_fusion.py --run-dir artifacts/runs/stage3_NEW
& $pythonSma src/evaluation/run_assertion_quality_evaluation.py --workbook outputs/fyp_gold_annotation_2026-10-01/SMA人工标注集_400条_最终全表复核版.xlsx --run-dir artifacts/runs/assertion_replay_NEW --replay-model-dir artifacts/runs/assertion_quality_repair_2026-10-02
& $pythonSma src/evaluation/run_fyp_evaluation.py --workbook outputs/fyp_gold_annotation_2026-10-01/SMA人工标注集_400条_最终全表复核版.xlsx --run-dir artifacts/runs/fyp_NEW --alignment-policy typed_orthographic_identity_v2_semantic_review_only --label-provenance human_confirmed_all --provenance-note 'User confirmed all 400 human-assigned labels; ChatGPT formatted only'
& $pythonSma src/evaluation/build_fyp_repair_report.py --run-dir artifacts/runs/fyp_NEW --quality-run-dir artifacts/runs/assertion_replay_NEW --identity-run-dir artifacts/runs/stage3_identity_repair_2026-10-02
& $pythonSma src/evaluation/build_fyp_graph_explorer.py --run-dir artifacts/runs/fyp_NEW --quality-run-dir artifacts/runs/assertion_replay_NEW
& $pythonSma src/database/neo4j_importer.py --quality-file artifacts/runs/assertion_replay_NEW/assertion_quality_full.jsonl --summary-file artifacts/runs/fyp_NEW/database_acceptance.json
& $pythonSma src/evaluation/audit_fyp_completion.py --run-dir artifacts/runs/fyp_NEW --attempt-live-db
& $pythonSma -m unittest discover -s tests/unit -v
```

Source workbook SHA-256 remains
`8316aee46846b70b1863d8884f2c75b12e832965dfed2ddcc0014e70b0eba697`;
raw extraction remains
`0d23d5dd162744dd70228905e6367800658e5d0af0b7328df50a6e62bfde76cb`;
repaired fused file
`ecdd5e68a308309f423b5ade455d14131152f67dcf978579c9f254c9d7de0e5d`.

## Database queries and recovery

All current queries must be scoped to the active version. No default destructive
clear exists. Importing a different source-context sidecar creates another
version; that is why unscoped counts include several snapshots.

```cypher
MATCH (m:SMAGraphMetadata {name:'active'}) RETURN m.graph_version, m.previous_version;
MATCH (m:SMAGraphMetadata {name:'active'})
MATCH (n:SMAEntity) WHERE n.graph_version=m.graph_version
RETURN n.namespace,n.type,count(*) ORDER BY n.namespace,n.type;
MATCH (m:SMAGraphMetadata {name:'active'})
MATCH (a:SMAEntity)-[r]->(b:SMAEntity) WHERE r.graph_version=m.graph_version
RETURN r.source,count(*) ORDER BY r.source;
MATCH (m:SMAGraphMetadata {name:'active'})
MATCH (n:SMAEntity) WHERE n.graph_version=m.graph_version AND n.namespace='literature'
AND n.type='Gene' AND n.name IN ['SMN1','SMN2']
RETURN n.name,n.ncbi_gene,n.entity_key;
MATCH (m:SMAGraphMetadata {name:'active'})
MATCH (a:SMAEntity)-[r]->(b:SMAEntity) WHERE r.graph_version=m.graph_version
AND a.name='Nusinersen' AND b.name='SMN2' AND r.source='Literature_NLP'
RETURN type(r),r.evidence_pmids,r.assertion_records_json;
```

For deliberate rollback, inspect and revalidate the previous typed snapshot
first, then set only metadata's active pointer to that verified version; do not
delete either graph. The original untyped graph remains queryable via `Entity`
for historical comparisons. Offline canonical backups and promotion hashes are
under Stage3 and the final run's `pre_promotion/`/`promotion.json`.

## Functional acceptance and limits

56 unit tests passed, including typed same-name mapping/frequency, distinct
SMN IDs/subtypes, source-separated parallel edges, unchanged provenance,
conditional assertion/typing, verbatim complete quotes and decimal offsets.
Live acceptance checks every stored node/edge/evidence property, unique keys,
constraint presence and preserved historical counts. Separate read-only
completion audit reports zero missing PMID lists and zero mutations.

Real browser checks: corrected full statistical sentence/source offsets;
unchanged human support/span labels; separately labelled model decisions;
0-match search clearing stale detail; empty30-unit fusion queue; current
13,001/18,288/164 totals; distinct literature/OT SMN2 with sourceID; Gene/Protein
separation; SMN2 TARGETS filter; Nusinersen→SMN2 with all37 original PMID records;
complete context flags; paired precision/retention/error table; no console errors.
Screenshot and `ui_acceptance.json` are in the final run. These are developer
functional checks, not independent human usability or biomedical validation.

Full-label strict support is26.3%; retrospective combined test strict PPV46.7%
retains30/202 and14/55 strict positives. Intervals overlap the previous gate;
no adequate full-corpus quality or statistically reliable gain is inferred.
No independent agreement, recall/F1 or human mapping-correctness rate is reported.
GraphRAG/generated-answer citation/atomic-claim validation remain future work.
