# Prevent incompatible names and cross-type overwrites in alignment

Status: open

Audit: `artifacts/runs/fyp_evaluation_human_confirmed_2026-10-02/completion_audit.json`.
The dictionary→semantic snapshot transforms Gene SMN2 into SMN1 in 982 endpoint
occurrences across 618 PMIDs. SMA type III/type 3 transformations into type 2
also occur. These are occurrence counts, not an adjudicated error-rate estimate.
NCBI Gene assigns separate identifiers to SMN1 and SMN2 (6606 and 6607).

The aligner groups embeddings by type, but `global_alignment_map` uses name
alone as key. A synthetic reproduction executes the actual key and lookup
expressions and demonstrates Gene/Protein overwrite. There are 195 shared
multi-type names in the dictionary-mapped input. Connected-component merging
also permits a chain whose endpoints are below the threshold to one another.

Acceptance: use typed alignment keys and typed frequency accounting; protect
authoritative incompatible gene identifiers and subtype/variant qualifiers;
do not equate similarity with identity or rely on an increased threshold alone.
Run a versioned controlled comparison, evaluate frozen changed mappings,
preserve source fields/counts, and present quality/coverage trade-offs. Do not
overwrite existing canonical graph data before validation. No model calls or
alignment changes were made by this audit.
