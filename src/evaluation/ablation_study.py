import json
import os
import networkx as nx

def load_graph_from_jsonl(filepath):
    G = nx.DiGraph()
    if not os.path.exists(filepath):
        print(f"Warning: File not found {filepath}")
        return G
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            row = json.loads(line)
            e1 = row.get('entity_1', {}).get('name')
            e2 = row.get('entity_2', {}).get('name')
            if e1 and e2:
                # We normalize text to avoid trivial case mismatches inflating nodes
                e1 = str(e1).strip().lower()
                e2 = str(e2).strip().lower()
                
                G.add_node(e1)
                G.add_node(e2)
                G.add_edge(e1, e2)
    return G

def calculate_metrics(G):
    if len(G) == 0:
        return 0, 0, 0.0, 0.0
    
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()
    
    # Average node degree (in + out) for directed graph `degree()` treats in+out
    total_degrees = sum(dict(G.degree()).values())
    avg_degree = total_degrees / total_nodes
    
    # Isolated Nodes Ratio (Nodes outside the Largest Weakly Connected Component)
    wcc = list(nx.weakly_connected_components(G))
    if wcc:
        largest_wcc = max(wcc, key=len)
        isolated_nodes_count = total_nodes - len(largest_wcc)
        isolated_ratio = isolated_nodes_count / total_nodes
    else:
        isolated_ratio = 1.0
        
    return total_nodes, total_edges, avg_degree, isolated_ratio

def main():
    print("==================================================")
    print("   ABLATION STUDY: GRAPH TOPOLOGY METRICS")
    print("==================================================")
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    pre_fusion_file = os.path.join(BASE_DIR, 'data', 'processed', 'extracted_triples.jsonl')
    post_fusion_file = os.path.join(BASE_DIR, 'data', 'processed', 'fused_triples.jsonl')
    
    G_pre = load_graph_from_jsonl(pre_fusion_file)
    G_post = load_graph_from_jsonl(post_fusion_file)
    
    n_pre, e_pre, d_pre, i_pre = calculate_metrics(G_pre)
    n_post, e_post, d_post, i_post = calculate_metrics(G_post)
    
    print(f"{'Metric':<25} | {'Pre-Fusion (State A)':<22} | {'Post-Fusion (State B)':<22}")
    print("-" * 75)
    print(f"{'Total Nodes':<25} | {n_pre:<22} | {n_post:<22}")
    print(f"{'Total Edges':<25} | {e_pre:<22} | {e_post:<22}")
    print(f"{'Average Node Degree':<25} | {d_pre:<22.4f} | {d_post:<22.4f}")
    print(f"{'Isolated Nodes Ratio':<25} | {i_pre:<22.2%} | {i_post:<22.2%}")
    print("==================================================")

if __name__ == "__main__":
    main()
