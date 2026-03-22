import json
import logging
import sys
import subprocess
from collections import defaultdict
from pathlib import Path

# Auto-install
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "scikit-learn"])
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_canonical_name(cluster, freq_map):
    # Retrieve the name with highest frequency. If tie, sort alphabetically for stability.
    return max(cluster, key=lambda x: (freq_map[x], x))

def main():
    input_file = Path("data/interim/mapped_triples.jsonl")
    output_file = Path("data/interim/aligned_triples.jsonl")
    
    if not input_file.exists():
        logging.error(f"Input file {input_file} not found.")
        return
        
    logging.info("Loading triples for semantic alignment...")
    triples = []
    entity_freq = defaultdict(int) 
    type_to_entities = defaultdict(set)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            triples.append(data)
            
            e1 = data.get("entity_1", {}).get("name", "")
            t1 = data.get("entity_1", {}).get("type", "")
            e2 = data.get("entity_2", {}).get("name", "")
            t2 = data.get("entity_2", {}).get("type", "")
            if not e1 or not e2: continue
            
            entity_freq[e1] += 1
            entity_freq[e2] += 1
            type_to_entities[t1].add(e1)
            type_to_entities[t2].add(e2)
            
    logging.info("Loading SentenceTransformer model...")
    import os
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2') 
    except Exception as e:
        logging.warning(f"HuggingFace mirror blocked/failed: {e}")
        logging.warning("Bypassing fuzzy semantic alignment. Proceeding purely with dictionary-mapped alignments.")
        import shutil
        shutil.copy(input_file, output_file)
        return
        
    global_alignment_map = {}
    
    for etype, entities in type_to_entities.items():
        if len(entities) <= 1:
            for e in entities:
                global_alignment_map[e] = e
            continue
            
        entity_list = list(entities)
        logging.info(f"Computing embeddings for {len(entity_list)} entities of type '{etype}'...")
        embeddings = model.encode(entity_list)
        sim_matrix = cosine_similarity(embeddings)
        
        # Simple Connected Components for clustering (>0.88)
        visited = set()
        for i in range(len(entity_list)):
            if i in visited: continue
            
            cluster = [entity_list[i]]
            visited.add(i)
            
            for j in range(i + 1, len(entity_list)):
                if j in visited: continue
                if sim_matrix[i][j] >= 0.88:
                    cluster.append(entity_list[j])
                    visited.add(j)
                    
            canonical = get_canonical_name(cluster, entity_freq)
            for e in cluster:
                global_alignment_map[e] = canonical
                
    logging.info("Applying canonical alignments over dataset...")
    aligned_count = 0
    with open(output_file, 'w', encoding='utf-8') as f:
        for data in triples:
            e1 = data.get("entity_1", {}).get("name", "")
            e2 = data.get("entity_2", {}).get("name", "")
            
            if "entity_1" in data: data["entity_1"]["name"] = global_alignment_map.get(e1, e1)
            if "entity_2" in data: data["entity_2"]["name"] = global_alignment_map.get(e2, e2)
            
            f.write(json.dumps(data) + "\n")
            aligned_count += 1
            
    logging.info(f"Alignment complete. Wrote {aligned_count} triples to {output_file}.")

if __name__ == "__main__":
    main()
