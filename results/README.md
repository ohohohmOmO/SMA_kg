# Results

This directory stores generated outputs that are useful for review,
reproducibility, or presentation but are not canonical pipeline inputs.

## reports

Text reports and captured command output from evaluation, topology, and combined
pipeline runs.

## runs

Dated reproduction runs. Each run directory should keep command logs, a manifest
with counts and hashes, and snapshot copies when the run needs to be auditable.
Canonical pipeline data that downstream code reads still belongs under `data/`.
When a stage cannot be fully rerun because a required local secret or external
service is unavailable, the run directory should include a small blocked log and
make clear which downstream artifacts are historical versus newly reproduced.

## test-results

Ad hoc API test outputs, including Open Targets GraphQL test responses.

## visualizations

Generated presentation outputs, including the canonical interactive graph
viewer and its local browser dependencies.

Pipeline data products that are consumed by source code remain under `data/`.

Historical manifests under `runs/` preserve the paths recorded when those runs
were created. A manifest may therefore mention the former `results/` location;
the run directory itself now lives under `results/runs/`.
