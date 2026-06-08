# Domain Docs

How the engineering skills should consume this repo's domain documentation when
exploring the codebase.

## Before exploring, read these

- `CONTEXT.md` at the repo root, if it exists.
- `docs/adr/`, if it exists, for ADRs that touch the area about to be changed.
- `README.md` when broader current project context is needed.
- `docs/archive/SMA_KG_Project_Overview_OLD.md` only when historical context is
  needed; prefer the dated handoff snapshot for the 2026-06-08 project state.

If any of these files do not exist, proceed silently. Do not flag their absence
or create them upfront unless the current task needs them.

## Layout

This is a single-context repository. The project centers on one SMA knowledge
graph pipeline with module directories for acquisition, extraction, fusion,
database import, and evaluation.

Expected optional structure:

```text
/
|-- CONTEXT.md
|-- docs/
|   |-- adr/
|   |-- agents/
|-- src/
|   |-- crawler/
|   |-- extraction/
|   |-- fusion/
|   |-- database/
|   |-- evaluation/
```

## Use project vocabulary

When output names a domain concept, prefer the terms already used by the repo:
SMA knowledge graph, biomedical triples, semantic fusion, Open Targets, PubMed,
Qwen/SiliconFlow extraction, Neo4j import, topology metrics, ablation study, and
novelty discovery.

If a concept is unclear, inspect the existing project documents before inventing
new terminology.
