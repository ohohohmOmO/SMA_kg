# Repository Entry Instructions

This root file is intentionally short so agent-aware tools can discover the
repository workflow without duplicating the full documentation.

Before running any command, test, script, or pipeline step, read:

1. `docs/start-here/PLAN.md`
2. `docs/start-here/AGENT_GUIDE.md`

After context loss or when the current state is uncertain, read every file
listed in `docs/start-here/README.md` in its prescribed order. Before diagnosing
an error or unexpected result, read `docs/start-here/ISSUE_LOG.md`.

Non-negotiable rules:

- Use the `KG_SMA_env` conda environment.
- Keep real secrets only in ignored `.env` or `.env.local` files.
- Preserve canonical data unless a validated promotion step explicitly changes
  it.
- Use dated run directories under `results/runs/`.
- Stage and commit file changes before the final response unless the user asks
  otherwise.
- AI application engineering work must use a branch named
  `feature/huawei-ai应用工程师-ai技术应用/<specific-feature>-<timestamp>`.

The complete workflow, environment, issue tracker, and domain documentation
rules live in `docs/start-here/AGENT_GUIDE.md`.
