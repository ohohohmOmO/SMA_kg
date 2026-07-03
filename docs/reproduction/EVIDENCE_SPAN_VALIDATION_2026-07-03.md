# Evidence Span Validation - 2026-07-03

## Scope

This change verifies that every newly extracted LLM `evidence_text` can be
located in the PubMed abstract identified by `source_pmid`. It adds a read-only
audit for existing triples and does not automatically rewrite canonical data.

## Alignment Contract

Accepted records contain:

```json
{
  "evidence_alignment": {
    "valid": true,
    "method": "exact",
    "score": 1.0,
    "start_char": 0,
    "end_char": 95,
    "matched_text": "original abstract span"
  }
}
```

Alignment proceeds in this order:

1. Case-insensitive exact substring match.
2. Match after ignoring punctuation, whitespace, and case while preserving
   original abstract offsets.
3. Conservative local fuzzy match for evidence of at least four tokens and 20
   normalized characters.

Fuzzy candidates must contain every evidence token, including repeated tokens,
and then reach the default 0.90 similarity threshold. This permits source spans
with a small number of inserted modifiers while rejecting replaced biomedical
entities.

## Pipeline Integration

- `src/extraction/llm_extractor.py` rejects non-aligned model evidence before
  writing extraction output.
- `src/extraction/run_stage2_extraction.py` requires valid alignment metadata
  for reusable LLM chunks and canonical LLM-only promotion.
- `src/biomedical/confidence.py` uses the alignment score as the evidence
  component for new records and labels the scoring version
  `raw_v2_evidence_aligned`.
- `src/extraction/validate_evidence_spans.py` audits historical outputs into
  accepted and rejected run artifacts without promotion.

## Verification

```powershell
python -m py_compile src/biomedical/evidence.py src/biomedical/confidence.py src/extraction/llm_extractor.py src/extraction/run_stage2_extraction.py src/extraction/validate_evidence_spans.py tests/unit/test_evidence_alignment.py
python -m unittest discover -s tests/unit -v
python src/extraction/validate_evidence_spans.py --run-dir results/runs/evidence_span_audit_2026-07-03_235108 --min-fuzzy-score 0.9
python src/extraction/llm_extractor.py --offset 0 --limit 1 --min-triples 0 --output-file results/runs/evidence_span_live_probe_2026-07-03_235534/extracted.jsonl --rejected-file results/runs/evidence_span_live_probe_2026-07-03_235534/rejected.jsonl
```

Results:

- Unit tests: 39 passed.
- Audit input: 18288 canonical Stage 2 triples.
- Aligned: 16214 (88.6592%).
- Exact: 15844.
- Normalized: 229.
- Conservative fuzzy: 141.
- Isolated for review: 2074.
- Bad JSON lines: 0.
- Audit runtime after token-coverage optimization: about 41 seconds.
- Live probe input: 1 abstract, PMID 42260294.
- Live probe output: 8 exact-aligned triples, 0 rejected.
- Canonical data mutated: false.

## Interpretation

The 2074 rejected historical records are not automatically false. They include
possible paraphrases, evidence assembled from non-contiguous abstract phrases,
and unsupported model text. They remain review candidates until a separate
human or semantic-entailment process decides whether to retain them.

This feature proves source-span presence, not that the extracted relation is a
correct interpretation of that span.
