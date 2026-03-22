import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DICTIONARY = {
    "drug": {
        "nusinersen": "Nusinersen",
        "spinraza": "Nusinersen",
        "risdiplam": "Risdiplam",
        "evrysdi": "Risdiplam",
        "zolgensma": "Onasemnogene Abeparvovec",
        "oa": "Onasemnogene Abeparvovec",
        "onasemnogene abeparvovec": "Onasemnogene Abeparvovec",
        "onasemnogene": "Onasemnogene Abeparvovec"
    },
    "disease": {
        "sma": "Spinal Muscular Atrophy",
        "spinal muscular atrophy": "Spinal Muscular Atrophy",
        "sma type 1": "Spinal Muscular Atrophy Type 1",
        "sma1": "Spinal Muscular Atrophy Type 1"
    },
    "gene": {
        "smn1": "SMN1",
        "smn2": "SMN2",
        "smn": "SMN",
        "exon 7": "SMN2 (Exon 7)"
    }
}

def map_entity(entity):
    name = entity.get("name", "")
    etype = entity.get("type", "").lower()
    lower_name = name.lower().strip()
    
    if etype in DICTIONARY and lower_name in DICTIONARY[etype]:
        entity["name"] = DICTIONARY[etype][lower_name]
    return entity

def main():
    input_file = Path("data/processed/extracted_triples.jsonl")
    output_dir = Path("data/interim")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "mapped_triples.jsonl"
    
    if not input_file.exists():
        logging.error(f"File {input_file} not found!")
        return
        
    mapped_count = 0
    with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
        for line in f_in:
            if not line.strip(): continue
            data = json.loads(line)
            
            data["entity_1"] = map_entity(data["entity_1"])
            data["entity_2"] = map_entity(data["entity_2"])
            
            f_out.write(json.dumps(data) + "\n")
            mapped_count += 1
            
    logging.info(f"Dictionary mapping complete. Processed {mapped_count} triples to {output_file}.")

if __name__ == "__main__":
    main()
