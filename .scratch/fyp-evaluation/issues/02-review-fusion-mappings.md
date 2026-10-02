# Review fixed 30 changed-mapping units

Status: optional-human-evidence-for-mapping-quality-rate

Queue: `artifacts/runs/fyp_evaluation_2026-10-02/fusion_review_30.jsonl`.
Latest equivalent queue: `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/fusion_review_30.jsonl`.
Uniform changed-mapping sample, seed 20261002; source contexts attached.
The offline explorer collects same/different/unclear judgments and exports JSON.

Acceptance: actual reviewer/date, both changed-step judgments, rationale for
different/unclear; hash/identity validation via summarize_fusion_review.py.
Report sampling limits and unknowns. Extraction support is not mapping truth.

The user's confirmation covers the 400 extraction labels, not these new
mapping judgments. Freeze the mapping condition being judged; after changing
alignment rules, retain the old judgments and prepare a versioned new queue
or reuse only judgments whose protected mapping fields remain identical.

Current queue: `artifacts/runs/fyp_four_repairs_final_2026-10-02/fusion_review_30.jsonl`. This repaired identity condition differs from the historical semantic baseline; no judgments transferred. Known identity defects have automated full-corpus regression evidence; human mapping judgments remain necessary only if a mapping-correctness rate is claimed.
