# Graph RAG Hard Citation Validation - 2026-07-03

## Scope

This change upgrades Graph RAG answer citations from prompt-only instructions
to a locally enforced evidence contract. It does not mutate the canonical
knowledge graph.

## Implementation

- Question Evidence Context records receive stable `T`, `F`, and optional `N`
  evidence IDs.
- Contexts expose explicit `allowed_citation_pmids` and
  `allowed_evidence_ids`.
- Fused-edge and Neo4j PMID lists are restricted to the citation allowlist
  before entering the answer prompt.
- The LLM returns claim-level PMID and evidence-ID references instead of an
  unaudited free-form answer.
- Local validation rejects unknown PMIDs, unknown evidence IDs, PMID/evidence
  mismatches, uncited claims, invalid confidence values, and undisclosed
  conflict contexts.
- Invalid output receives up to the configured number of correction attempts.
- Exhausted validation returns a zero-confidence safe fallback without
  exposing unvalidated claims or citations.
- Final answer text and top-level supporting PMIDs are derived locally from
  validated claims.

## Verification

Commands used the repository `KG_SMA_env` Python:

```powershell
python -m py_compile src/evidence/context_builder.py src/qa/retriever.py src/qa/neo4j_neighborhood.py src/qa/answer_validation.py src/qa/answer.py src/qa/run_graph_rag.py tests/unit/test_answer_validation.py tests/unit/test_evidence_context.py tests/unit/test_graph_rag.py
python -m unittest discover -s tests/unit -v
python src/qa/run_graph_rag.py --question "How does Nusinersen affect motor function?" --retrieval-mode hybrid_tfidf --validation-attempts 2 --output-file artifacts/runs/graph_rag_hard_citation_probe_2026-07-03_232240/answer_live.json
```

Results:

- Unit tests: 31 passed.
- Canonical dry-run context: 32 allowed PMIDs, 24 aligned triples, 16 fused
  edges, 40 allowed evidence IDs, and 16 bounded fused PMID lists.
- Live answer: validation passed on attempt 1.
- Live answer claims: 1.
- Live supporting PMIDs: 3.
- Live limitations: 3, including disclosure of conflicting graph evidence.
- Canonical graph mutated: false.

## Boundary

Hard citation validation proves that returned PMID and evidence references
belong to the supplied Evidence Context and agree with one another. It does not
prove semantic entailment between claim text and the cited abstract span.
Evidence-span verification remains a separate follow-up.
