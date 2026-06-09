import json
import logging
from pathlib import Path
import argparse

import pandas as pd
from pyvis.network import Network
import networkx as nx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_color(etype):
    etype = etype.lower()
    if etype == "gene": return "#e74c3c" # Natively render distinct nodes mapping parameters red
    if etype == "drug": return "#2ecc71" # Target array elements natively green
    if "phenotype" in etype or "disease" in etype: return "#3498db" # Isolate base tags universally blue
    return "#95a5a6"


def strip_trailing_whitespace(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    Path(path).write_text(cleaned, encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate an interactive PyVis graph viewer.")
    parser.add_argument("--input-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--metrics-file", default="data/processed/analytics_metrics.csv")
    parser.add_argument("--opentargets-file", default="data/external/sma_gda_baseline.jsonl")
    parser.add_argument("--output-file", default="docs/graph_viewer.html")
    return parser.parse_args()

def main():
    args = parse_args()
    fused_file = Path(args.input_file)
    metrics_file = Path(args.metrics_file)
    
    if not fused_file.exists():
        logging.error("Source fused graph logic not found.")
        return 1

    metrics_map = {}
    if metrics_file.exists():
        df_metrics = pd.read_csv(metrics_file)
        for _, row in df_metrics.iterrows():
            metrics_map[row["Entity"]] = {
                "pagerank": row["PageRank"],
                "community": row["Community_ID"]
            }

    logging.info("Initializing cleanly encapsulated standalone PyVis interactive HTML bounds...")
    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#333333", directed=True)
    net.force_atlas_2based()
    
    added_nodes = set()
    
    def add_node_safe(name, etype):
        if name not in added_nodes:
            pr = metrics_map.get(name, {}).get("pagerank", 0.005)
            comm = metrics_map.get(name, {}).get("community", "N/A")
            size = max(12, min(65, pr * 1000))
            
            title_html = f"<b>{name}</b><br>Type: {etype}<br>Community Array: {comm}<br>PageRank Gravity: {pr:.4f}"
            net.add_node(name, label=name, title=title_html, color=get_color(etype), size=size)
            added_nodes.add(name)

    with open(fused_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            e1 = data["entity_1"]["name"]
            t1 = data["entity_1"].get("type", "Unknown")
            e2 = data["entity_2"]["name"]
            t2 = data["entity_2"].get("type", "Unknown")
            rel = data.get("relation", "")
            
            add_node_safe(e1, t1)
            add_node_safe(e2, t2)
            
            conf = data.get("computed_confidence", 0.0)
            net.add_edge(e1, e2, title=f"Relation Bounds: {rel}<br>Accuracy Edge: {conf}", label=rel, physics=True)

    ot_file = Path(args.opentargets_file)
    if ot_file.exists():
        disease_name = "Spinal Muscular Atrophy"
        add_node_safe(disease_name, "Disease")
        with open(ot_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                gene = data["gene_symbol"]
                score = data.get("score", 0.0)
                add_node_safe(gene, "Gene")
                net.add_edge(gene, disease_name, title=f"Relation: ASSOCIATED_WITH<br>Graph Target Score: {score}", label="ASSOCIATED_WITH", physics=True, color="#bdc3c7")

    out_html = Path(args.output_file)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    
    net.save_graph(str(out_html))
    strip_trailing_whitespace(out_html)
    logging.info(f"Topological interactive network visualization universally packaged down successfully out to {out_html}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
