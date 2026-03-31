import json
import os
import pandas as pd
import random

def main():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    input_file = os.path.join(BASE_DIR, 'data', 'processed', 'fused_triples.jsonl')
    output_file = os.path.join(BASE_DIR, 'data', 'processed', 'human_evaluation_sample.csv')
    
    triples = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                triples.append(json.loads(line))
    except Exception as e:
        print(f"Error loading fused triples: {e}")
        return

    # Sample EXACTLY 100 random triples 
    sample_size = 100
    if len(triples) < sample_size:
        print(f"Warning: Only {len(triples)} triples available, cannot sample {sample_size}. Sampling all.")
        sample_size = len(triples)
        
    random.seed(42)
    sampled_triples = random.sample(triples, sample_size)
    
    data_for_export = []
    for row in sampled_triples:
        e1_name = row.get('entity_1', {}).get('name', '')
        e2_name = row.get('entity_2', {}).get('name', '')
        relation = row.get('relation', '')
        
        evidence = row.get('evidence', {})
        pmids = ",".join(evidence.get('pmid_list', []))
        extracted_by = ",".join(evidence.get('extraction_engines', []))
        
        data_for_export.append({
            "Entity_1": e1_name,
            "Relation": relation,
            "Entity_2": e2_name,
            "Evidence_PMIDs": pmids,
            "Extracted_By": extracted_by,
            "Human_Score": ""
        })
        
    df = pd.DataFrame(data_for_export)
    df.to_csv(output_file, index=False, columns=["Entity_1", "Relation", "Entity_2", "Evidence_PMIDs", "Extracted_By", "Human_Score"])
    
    print(f"Successfully generated human evaluation sample of {sample_size} triples at {output_file}.")

if __name__ == "__main__":
    main()
