# Artifacts

This directory stores historical run outputs that were previously loose in the
repository root.

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

Pipeline data products that are consumed by source code remain under `data/`.
