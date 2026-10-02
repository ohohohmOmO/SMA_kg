import json
import logging
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.biomedical.entity_identity import entity_id

import networkx as nx
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

COMMUNITY_SEED = 42

def build_networkx_from_jsonl(filepath):
    G = nx.MultiDiGraph()
    if not Path(filepath).exists():
        logging.error(f"File {filepath} not found.")
        return G
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            e1 = entity_id(data["entity_1"])
            e1_type = data["entity_1"].get("type", "Unknown")
            e2 = entity_id(data["entity_2"])
            e2_type = data["entity_2"].get("type", "Unknown")
            
            G.add_node(e1, type=e1_type, name=data["entity_1"]["name"], namespace="literature", source_id="")
            G.add_node(e2, type=e2_type, name=data["entity_2"]["name"], namespace="literature", source_id="")
            
            conf = data.get("computed_confidence", 0.5)
            G.add_edge(e1, e2, key="literature:" + data["relation"], weight=conf)
            
    return G

def parse_args():
    parser = argparse.ArgumentParser(description="Compute deterministic local graph analytics.")
    parser.add_argument("--input-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--opentargets-file", default="data/external/sma_gda_baseline.jsonl")
    parser.add_argument("--output-file", default="data/processed/analytics_metrics.csv")
    return parser.parse_args()

def main():
    args = parse_args()
    fused_file = args.input_file
    out_file = Path(args.output_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.info("Building NetworkX graph from offline fused triples...")
    G = build_networkx_from_jsonl(fused_file)
    
    ot_file = Path(args.opentargets_file)
    if ot_file.exists():
        with open(ot_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                gene = entity_id({"name": data["target_id"], "type": "Gene"}, "opentargets")
                disease = entity_id({"name": data["disease_id"], "type": "Disease"}, "opentargets")
                G.add_node(gene, type="Gene", name=data["gene_symbol"], namespace="opentargets", source_id=data["target_id"])
                G.add_node(disease, type="Disease", name=data["disease_id"], namespace="opentargets", source_id=data["disease_id"])
                G.add_edge(gene, disease, key="opentargets:ASSOCIATED_WITH", weight=data.get("score", 0.0))
    
    if len(G.nodes) == 0:
        logging.error("Graph is empty. Cannot compute analytics.")
        return 1

    logging.info(f"Graph natively loaded over standard memory bounds. Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")
    
    logging.info("Computing mathematical PageRank Centrality constraints natively...")
    pagerank_scores = nx.pagerank(G, weight="weight")
    
    logging.info("Computing modularity Louvain Community Detection components...")
    try:
        undirected_G = G.to_undirected()
        communities = nx.community.louvain_communities(undirected_G, weight="weight", seed=COMMUNITY_SEED)
        communities = sorted(communities, key=lambda comm: sorted(comm)[0])
        
        community_map = {}
        for c_id, comm in enumerate(communities):
            for node in sorted(comm):
                community_map[node] = c_id
    except AttributeError:
        community_map = {n: 0 for n in G.nodes}
        logging.warning("Community detection scaling skipped due to old local networkx mathematical parameters.")

    records = []
    for node in sorted(G.nodes):
        records.append({
            "Entity": G.nodes[node]["name"],
            "EntityId": node,
            "Type": G.nodes[node].get("type", "Unknown"),
            "Namespace": G.nodes[node]["namespace"],
            "SourceId": G.nodes[node]["source_id"],
            "PageRank": pagerank_scores.get(node, 0.0),
            "Community_ID": community_map.get(node, -1)
        })
        
    df = pd.DataFrame(records).sort_values(by=["PageRank", "EntityId"], ascending=[False, True])
    df.to_csv(out_file, index=False)
    logging.info(f"Topology analytics logic entirely complete! Top nodes structurally aligned successfully out to {out_file}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
