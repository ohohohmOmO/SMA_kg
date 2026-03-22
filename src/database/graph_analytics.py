import json
import logging
from pathlib import Path
import sys
import subprocess

try:
    import networkx as nx
    import pandas as pd
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx", "pandas"])
    import networkx as nx
    import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def build_networkx_from_jsonl(filepath):
    G = nx.DiGraph()
    if not Path(filepath).exists():
        logging.error(f"File {filepath} not found.")
        return G
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            e1 = data["entity_1"]["name"]
            e1_type = data["entity_1"].get("type", "Unknown")
            e2 = data["entity_2"]["name"]
            e2_type = data["entity_2"].get("type", "Unknown")
            
            G.add_node(e1, type=e1_type)
            G.add_node(e2, type=e2_type)
            
            conf = data.get("computed_confidence", 0.5)
            G.add_edge(e1, e2, weight=conf)
            
    return G

def main():
    fused_file = "data/processed/fused_triples.jsonl"
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "analytics_metrics.csv"
    
    logging.info("Building NetworkX graph from offline fused triples...")
    G = build_networkx_from_jsonl(fused_file)
    
    ot_file = Path("data/external/sma_gda_baseline.jsonl")
    if ot_file.exists():
        with open(ot_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                gene = data["gene_symbol"]
                disease = "Spinal Muscular Atrophy"
                G.add_node(gene, type="Gene")
                G.add_node(disease, type="Disease")
                G.add_edge(gene, disease, weight=data.get("score", 0.0))
    
    if len(G.nodes) == 0:
        logging.error("Graph is empty. Cannot compute analytics.")
        return

    logging.info(f"Graph natively loaded over standard memory bounds. Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")
    
    logging.info("Computing mathematical PageRank Centrality constraints natively...")
    pagerank_scores = nx.pagerank(G, weight="weight")
    
    logging.info("Computing modularity Louvain Community Detection components...")
    try:
        undirected_G = G.to_undirected()
        communities = nx.community.louvain_communities(undirected_G, weight="weight")
        
        community_map = {}
        for c_id, comm in enumerate(communities):
            for node in comm:
                community_map[node] = c_id
    except AttributeError:
        community_map = {n: 0 for n in G.nodes}
        logging.warning("Community detection scaling skipped due to old local networkx mathematical parameters.")

    records = []
    for node in G.nodes:
        records.append({
            "Entity": node,
            "Type": G.nodes[node].get("type", "Unknown"),
            "PageRank": pagerank_scores.get(node, 0.0),
            "Community_ID": community_map.get(node, -1)
        })
        
    df = pd.DataFrame(records).sort_values(by="PageRank", ascending=False)
    df.to_csv(out_file, index=False)
    logging.info(f"Topology analytics logic entirely complete! Top nodes structurally aligned successfully out to {out_file}.")

if __name__ == "__main__":
    main()
