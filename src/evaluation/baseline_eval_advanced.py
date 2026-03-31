import json
import os
import pandas as pd

def normalize_text(text):
    return str(text).strip().lower()

def main():
    print("==================================================")
    print("   ADVANCED BASELINE EVALUATION REPORT")
    print("==================================================")
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    baseline_file = os.path.join(BASE_DIR, 'data', 'external', 'sma_gda_baseline.jsonl')
    extracted_file = os.path.join(BASE_DIR, 'data', 'processed', 'extracted_triples.jsonl')
    
    # Load baseline
    baseline_genes = set()
    try:
        with open(baseline_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                baseline_genes.add(normalize_text(row['gene_symbol']))
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
                
                # Check entity 1
                if row.get('entity_1', {}).get('type') == 'Gene':
                    extracted_data[engine].add(normalize_text(row['entity_1'].get('name', '')))
                # Check entity 2
                if row.get('entity_2', {}).get('type') == 'Gene':
                    extracted_data[engine].add(normalize_text(row['entity_2'].get('name', '')))
                    
    except Exception as e:
        print(f"Error loading extracted triples: {e}")
        return

    print(f"Match Criteria: Exact Match (Normalized)")
    print(f"Total Baseline Genes (Ground Truth): {len(baseline_genes)}\n")

    for engine, ex_genes in extracted_data.items():
        ex_genes = {g for g in ex_genes if g} # remove empty
        
        tp_precision = 0
        fp = 0
        matched_baseline_genes = set()
        
        for ex_gene in ex_genes:
            matched = False
            if ex_gene in baseline_genes:
                matched = True
                matched_baseline_genes.add(ex_gene)
                    
            if matched:
                tp_precision += 1
            else:
                fp += 1
                
        tp_recall = len(matched_baseline_genes)
        fn = len(baseline_genes) - tp_recall
        
        precision = tp_precision / (tp_precision + fp) if (tp_precision + fp) > 0 else 0.0
        recall = tp_recall / (tp_recall + fn) if (tp_recall + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"--- Engine: {engine} ---")
        print(f"Total Extracted Genes: {len(ex_genes)}")
        print(f"Precision: {precision:.4f} (TP: {tp_precision}, FP: {fp})")
        print(f"Recall:    {recall:.4f} (TP: {tp_recall}, FN: {fn})")
        print(f"F1-Score:  {f1:.4f}\n")

    print("==================================================")

if __name__ == "__main__":
    main()
