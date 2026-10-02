# Stage 3 Fusion Run

- Valid: True
- Input file: `data/processed/extracted_triples.jsonl`
- Input SHA-256: `0d23d5dd162744dd70228905e6367800658e5d0af0b7328df50a6e62bfde76cb`
- Alignment model: `NeuML/pubmedbert-base-embeddings`
- Promoted: False

## Outputs

- `artifacts\runs\stage3_identity_repair_2026-10-02\outputs\data\interim\mapped_triples.jsonl`: records=18288, valid=True, sha256=`7f10841e68bcd54aeb58658562e1147b20c5a4502b8ef5928ef08c7637b9e4f8`
- `artifacts\runs\stage3_identity_repair_2026-10-02\outputs\data\interim\aligned_triples.jsonl`: records=18288, valid=True, sha256=`8bcb0a1863b36419160b7ac4072c0887a7d26aef552ee6fbf2caec68db854d5f`
- `artifacts\runs\stage3_identity_repair_2026-10-02\outputs\data\processed\fused_triples.jsonl`: records=13001, valid=True, sha256=`ecdd5e68a308309f423b5ade455d14131152f67dcf978579c9f254c9d7de0e5d`
- `artifacts\runs\stage3_identity_repair_2026-10-02\outputs\data\interim\relation_conflicts.jsonl`: records=36, valid=True, sha256=`1a39be9c5a60dd5517829cdfffce4fe825a7edd62745aed20b3b1e5d01cdea78`
- `artifacts\runs\stage3_identity_repair_2026-10-02\outputs\data\interim\aggregation_rejected.jsonl`: records=0, valid=True, sha256=`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Commands

- dictionary_mapper: exit_code=0, log=`artifacts\runs\stage3_identity_repair_2026-10-02\logs\dictionary_mapper.log`
- semantic_aligner: exit_code=0, log=`artifacts\runs\stage3_identity_repair_2026-10-02\logs\semantic_aligner.log`
- triples_aggregator: exit_code=0, log=`artifacts\runs\stage3_identity_repair_2026-10-02\logs\triples_aggregator.log`
