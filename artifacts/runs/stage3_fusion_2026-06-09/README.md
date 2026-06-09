# Stage 3 Fusion Run - 2026-06-09

This directory stores the reproducibility evidence for the Stage 3 rerun after
the stabilized Stage 2 extraction.

## Scope

Stage 3 covers:

- `src/fusion/dictionary_mapper.py`
- `src/fusion/semantic_aligner.py`
- `src/fusion/triples_aggregator.py`

Canonical pipeline outputs remain under `data/interim/` and `data/processed/`.
This run directory keeps logs, pre-run snapshots, output snapshots, a manifest,
and validation statistics.

## Results

- Input extracted triples: 5738
- Dictionary-mapped triples: 5738
- Semantically aligned triples: 5738
- Fused unique edges: 554
- Stage 4 fused-triples dry-read: passed

## Notes

A second semantic-alignment run against the same mapped input produced a
different `aligned_triples.jsonl` hash. The canonical aligned output was restored
to the first formal run so it remains consistent with this run's manifest and
fused output.
