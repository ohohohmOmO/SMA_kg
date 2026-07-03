# Stage 3 Fusion Run

- Valid: True
- Input file: `data/processed/extracted_triples.jsonl`
- Input SHA-256: `0d23d5dd162744dd70228905e6367800658e5d0af0b7328df50a6e62bfde76cb`
- Alignment model: `NeuML/pubmedbert-base-embeddings`
- Promoted: True

## Outputs

- `artifacts\runs\stage3_fusion_full_2026-06-09\outputs\data\interim\mapped_triples.jsonl`: records=18288, valid=True, sha256=`7f10841e68bcd54aeb58658562e1147b20c5a4502b8ef5928ef08c7637b9e4f8`
- `artifacts\runs\stage3_fusion_full_2026-06-09\outputs\data\interim\aligned_triples.jsonl`: records=18288, valid=True, sha256=`65fc3e961e37e5361b47dd46dccef4916575d0e3b71130a8e6c775a18b36e58e`
- `artifacts\runs\stage3_fusion_full_2026-06-09\outputs\data\processed\fused_triples.jsonl`: records=11155, valid=True, sha256=`1771293aad8258befe717c7c7ca00c349fe5fdb782b84245b1357ad45e332b5a`
- `artifacts\runs\stage3_fusion_full_2026-06-09\outputs\data\interim\relation_conflicts.jsonl`: records=59, valid=True, sha256=`96c8923c9d67776b00936169323ee092979870d40b15c5a932d37a022b2924db`
- `artifacts\runs\stage3_fusion_full_2026-06-09\outputs\data\interim\aggregation_rejected.jsonl`: records=0, valid=True, sha256=`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Commands

- dictionary_mapper: exit_code=0, log=`artifacts\runs\stage3_fusion_full_2026-06-09\logs\dictionary_mapper.log`
- semantic_aligner: exit_code=0, log=`artifacts\runs\stage3_fusion_full_2026-06-09\logs\semantic_aligner.log`
- triples_aggregator: exit_code=0, log=`artifacts\runs\stage3_fusion_full_2026-06-09\logs\triples_aggregator.log`
