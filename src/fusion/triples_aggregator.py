import json
import logging
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    input_file = Path("data/interim/aligned_triples.jsonl")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "fused_triples.jsonl"
    
    if not input_file.exists():
        logging.error(f"Input file {input_file} not found.")
        return
        
    logging.info("Aggregating aligned triples...")
    
    grouped_data = defaultdict(lambda: {
        "pmid_set": set(),
        "engines_set": set(),
        "max_conf": 0.0,
        "sample_data": None
    })
    
    raw_count = 0
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            raw_count += 1
            data = json.loads(line)
            
            e1_name = data["entity_1"].get("name", "")
            e1_type = data["entity_1"].get("type", "")
            rel = data.get("relation", "")
            e2_name = data["entity_2"].get("name", "")
            e2_type = data["entity_2"].get("type", "")
            
            key = (e1_name, e1_type, rel, e2_name, e2_type)
            
            group = grouped_data[key]
            group["pmid_set"].add(str(data.get("source_pmid", "UNKNOWN")))
            group["engines_set"].add(data.get("extracted_by", "UNKNOWN"))
            group["max_conf"] = max(group["max_conf"], data.get("computed_confidence", 0.0))
            
            if not group["sample_data"]:
                group["sample_data"] = data
                
    fused_triples = []
    for key, group in grouped_data.items():
        base = group["sample_data"]
        engines_list = list(group["engines_set"])
        
        # Boost confidence by 0.05 for every additional engine corroborating
        boost = 0.05 * (len(engines_list) - 1)
        final_conf = min(1.0, group["max_conf"] + boost)
        
        fused_triple = {
            "entity_1": base["entity_1"],
            "relation": base["relation"],
            "entity_2": base["entity_2"],
            "evidence": {
                "pmid_list": list(group["pmid_set"]),
                "extraction_engines": engines_list
            },
            "computed_confidence": round(final_conf, 3)
        }
        fused_triples.append(fused_triple)
        
    with open(output_file, 'w', encoding='utf-8') as f:
        for t in fused_triples:
            f.write(json.dumps(t) + "\n")
            
    logging.info(f"Aggregated {raw_count} raw triples tightly into {len(fused_triples)} fused unique edges.")
    logging.info(f"Saved to {output_file}.")

if __name__ == "__main__":
    main()
