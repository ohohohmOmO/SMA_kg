import json
import os

def normalize_text(text):
    return str(text).strip().lower()

SMA_SYNONYMS = {
    "sma", "spinal muscular atrophy", "sma type i", "sma type ii", "sma type iii", "sma type iv", 
    "sma type 1", "sma type 2", "sma type 3", "sma type 4", "sma type 0", "5q-sma", 
    "5q-spinal muscular atrophy", "type 1 sma", "type 2 sma", "type 3 sma", "type 4 sma", "type 0 sma", "type i sma"
}

def main():
    print("==================================================")
    print("   ADVANCED BASELINE EVALUATION REPORT")
    print("==================================================")
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    baseline_file = os.path.join(BASE_DIR, 'data', 'external', 'sma_gda_baseline.jsonl')
    extracted_file = os.path.join(BASE_DIR, 'data', 'processed', 'extracted_triples.jsonl')
    
    # Load baseline
    baseline_tuples = set()
    try:
        with open(baseline_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                gene = normalize_text(row['gene_symbol'])
                baseline_tuples.add((gene, 'sma'))
    except Exception as e:
        print(f"Error loading baseline: {e}")
        return

    # Load predictions
    extracted_data = {}
    try:
        with open(extracted_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                engine = row.get('extracted_by', 'Unknown')
                if engine not in extracted_data:
                    extracted_data[engine] = set()
                
                e1 = row.get('entity_1', {})
                e2 = row.get('entity_2', {})
                
                e1_type = e1.get('type', '')
                e2_type = e2.get('type', '')
                e1_name = normalize_text(e1.get('name', ''))
                e2_name = normalize_text(e2.get('name', ''))
                
                # Check (Gene, SMA)
                if e1_type in ['Gene', 'Protein'] and e2_name in SMA_SYNONYMS:
                    extracted_data[engine].add((e1_name, 'sma'))
                # Check (SMA, Gene)
                if e2_type in ['Gene', 'Protein'] and e1_name in SMA_SYNONYMS:
                    extracted_data[engine].add((e2_name, 'sma'))
                    
    except Exception as e:
        print(f"Error loading extracted triples: {e}")
        return

    print(f"Match Criteria: Exact Relational Match (Normalized Tuples)")
    print(f"Total Baseline Tuples (Ground Truth): {len(baseline_tuples)}\n")

    for engine, ex_tuples in extracted_data.items():
        tp = len(ex_tuples.intersection(baseline_tuples))
        fp = len(ex_tuples - baseline_tuples)
        fn = len(baseline_tuples - ex_tuples)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"--- Engine: {engine} ---")
        print(f"Total Extracted Gene-SMA Tuples: {len(ex_tuples)}")
        print(f"Precision: {precision:.4f} (TP: {tp}, FP: {fp})")
        print(f"Recall:    {recall:.4f} (TP: {tp}, FN: {fn})")
        print(f"F1-Score:  {f1:.4f}\n")

    print("==================================================")

if __name__ == "__main__":
    main()
