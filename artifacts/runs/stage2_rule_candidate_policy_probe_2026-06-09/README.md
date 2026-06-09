# Stage 2 Rule Candidate Policy Probe - 2026-06-09

Purpose: verify the post-decision Stage 2 policy that local rules produce
auxiliary `Rule_Candidate` triples rather than canonical graph evidence.

Commands:

```powershell
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src\extraction\local_pipeline.py --input-file data\raw\pubmed_sma_abstracts.jsonl --output-file artifacts\runs\stage2_rule_candidate_policy_probe_2026-06-09\rule_candidate_triples.jsonl --rejected-file artifacts\runs\stage2_rule_candidate_policy_probe_2026-06-09\rule_candidate_triples.rejected.jsonl --offset 200 --limit 5
& 'C:\Users\jon15\anaconda3\envs\KG_SMA_env\python.exe' src\extraction\verify_rule_candidates.py --input-file artifacts\runs\stage2_rule_candidate_policy_probe_2026-06-09\rule_candidate_triples.jsonl --abstracts-file data\raw\pubmed_sma_abstracts.jsonl --output-file artifacts\runs\stage2_rule_candidate_policy_probe_2026-06-09\verified_rule_triples.jsonl --rejected-file artifacts\runs\stage2_rule_candidate_policy_probe_2026-06-09\verified_rule_triples.rejected.jsonl --dry-run
```

Results:

- Rule candidates: 5
- Rule candidate rejections: 0
- Verifier dry run selected candidates: 5
- Missing source abstracts during verifier dry run: 0
- API calls during verifier dry run: 0
- Canonical output promotion: false
