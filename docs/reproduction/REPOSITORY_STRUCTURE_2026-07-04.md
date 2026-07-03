# Repository Structure Migration - 2026-07-04

## Goal

Make the repository understandable from its top-level directories while keeping
the Python package and canonical data interfaces stable.

## Structure

```text
docs/start-here/  current context and required operating documents
src/              production code grouped by pipeline function
tests/            unit and smoke verification
notebooks/        exploratory Stage 1 analysis
resources/        controlled biomedical schema and dictionaries
data/             reusable pipeline inputs, intermediates, and canonical data
results/          generated runs, reports, test outputs, and visualizations
```

Root `README.md` and `AGENTS.md` are short discovery entrypoints. They direct
people and tools to the complete documents in `docs/start-here/`.

## Compatibility Decisions

- `src/` was not renamed or wrapped in another directory. It is the stable
  Python import interface, and moving it would add path configuration without
  improving the implementation.
- `data/raw`, `data/external`, `data/interim`, and `data/processed` were kept.
  These lifecycle names are existing pipeline interfaces used by every Stage.
- The former `artifacts/` tree moved to `results/`. New default run directories
  are under `results/runs/`.
- The graph viewer and its relative `lib/` dependencies moved together to
  `results/visualizations/`.
- Historical run manifests were not rewritten. Their old `artifacts/...` paths
  are provenance captured at run time, not current path declarations.

## Verification

Run from the repository root with `KG_SMA_env`:

```powershell
python -m unittest discover -s tests/unit -v
python src/qa/build_index.py --retrieval-mode hybrid_tfidf --run-dir results/runs/repository_structure_graph_rag_probe_<stamp>
python src/database/run_stage4_graph.py --help
```

The migration does not promote or mutate canonical files under `data/`.

## Verified Result

- Python compilation passed for every source file whose default path changed.
- The full unit suite passed 39 tests.
- Graph RAG index probe:
  `results/runs/repository_structure_graph_rag_probe_2026-07-04_0032/`.
- The Graph RAG canonical index manifest was restored and has no Git diff after
  the probe.
- A full local PyVis generation produced a 4,844,692-byte standalone UTF-8 HTML
  file in the OS temp directory and did not recreate a root `lib/` directory.
- Static scanning found no active references to the former required-document,
  graph-viewer, or default run paths outside the explicit migration history.
