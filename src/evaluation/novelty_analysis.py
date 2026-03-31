import json
import os
import pandas as pd

def normalize_text(text):
    return str(text).strip().lower()

SMA_SYNONYMS = {
    "sma", "spinal muscular atrophy", "sma type i", "sma type ii", "sma type iii", "sma type iv", 
    "sma type 1", "sma type 2", "sma type 3", "sma type 4", "sma type 0", "5q-sma", 
    "5q-spinal muscular atrophy", "type 1 sma", "type 2 sma", "type 3 sma", "type 4 sma", "type 0 sma", "type i sma"
}

def main():
    print("==================================================")
    print("   NOVELTY DISCOVERY GENERATOR")
    print("==================================================")
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    baseline_file = os.path.join(BASE_DIR, 'data', 'external', 'sma_gda_baseline.jsonl')
    extracted_file = os.path.join(BASE_DIR, 'data', 'processed', 'extracted_triples.jsonl')
    output_file = os.path.join(BASE_DIR, 'data', 'processed', 'llm_novel_discoveries.csv')
    
    # Load baseline genes
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

    # Process Extractions
    novelties = {}
    total_triples = 0
    try:
        with open(extracted_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                total_triples += 1
                row = json.loads(line)
                
                # We only want LLM extractions
                if 'LLM' not in row.get('extracted_by', ''):
                    continue
                
                e1 = row.get('entity_1', {})
                e2 = row.get('entity_2', {})
                relation = row.get('relation', 'UNKNOWN')
                pmid = row.get('source_pmid', '')
                conf = row.get('computed_confidence', 0.0)
                
                e1_type = e1.get('type', '')
                e2_type = e2.get('type', '')
                e1_name = normalize_text(e1.get('name', ''))
                e2_name = normalize_text(e2.get('name', ''))
                e1_raw = e1.get('name', '')
                e2_raw = e2.get('name', '')
                
                novel_gene = None
                context_entity = None
                
                # Check (Gene, SMA)
                if e1_type in ['Gene', 'Protein'] and e2_name in SMA_SYNONYMS:
                    if e1_name not in baseline_genes:
                        novel_gene = e1_raw
                        context_entity = e2_raw
                # Check (SMA, Gene)
                elif e2_type in ['Gene', 'Protein'] and e1_name in SMA_SYNONYMS:
                    if e2_name not in baseline_genes:
                        novel_gene = e2_raw
                        context_entity = e1_raw
                        
                if novel_gene:
                    key = (normalize_text(novel_gene), relation, context_entity)
                    if key not in novelties:
                        novelties[key] = {
                            'Novel_Gene': novel_gene,
                            'Relation_Type': relation,
                            'Context_Entity': context_entity,
                            'Evidence_PMIDs': set(),
                            'Confidence_Score': []
                        }
                    novelties[key]['Evidence_PMIDs'].add(str(pmid))
                    novelties[key]['Confidence_Score'].append(float(conf))
                    
    except Exception as e:
        print(f"Error parsing extractions: {e}")
        return

    # Build DataFrame
    rows = []
    for data in novelties.values():
        pmids = sorted(list(data['Evidence_PMIDs']))
        avg_conf = sum(data['Confidence_Score']) / len(data['Confidence_Score']) if data['Confidence_Score'] else 0.0
        
        rows.append({
            'Novel_Gene': data['Novel_Gene'],
            'Relation_Type': data['Relation_Type'],
            'Context_Entity': data['Context_Entity'],
            'Evidence_PMIDs': ", ".join(pmids),
            'Number_of_Mentions': len(pmids),
            'Confidence_Score': round(avg_conf, 4)
        })
        
    df = pd.DataFrame(rows)
    # Sort by number of mentions descending (most prevalent discoveries first)
    if not df.empty:
        df = df.sort_values(by='Number_of_Mentions', ascending=False)
        
    df.to_csv(output_file, index=False)
    
    print(f"Parsed {total_triples} total triples.")
    print(f"Identified {len(df)} distinct novel False Positive relationships.")
    print(f"Exported to -> {output_file}")
    print("==================================================")

if __name__ == "__main__":
    main()
