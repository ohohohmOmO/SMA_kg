import json
import logging
from pathlib import Path
import argparse
import sys
from html import escape

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.biomedical.entity_identity import entity_id

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
            if "EntityId" not in row:
                raise ValueError("Metrics use historical name-only identity; rerun graph_analytics first")
            metrics_map[row["EntityId"]] = {
                "pagerank": row["PageRank"],
                "community": row["Community_ID"]
            }

    logging.info("Initializing cleanly encapsulated standalone PyVis interactive HTML bounds...")
    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#333333", directed=True, cdn_resources="in_line")
    net.force_atlas_2based()
    
    added_nodes = set()
    
    def add_node_safe(name, etype, namespace="literature", source_id=""):
        key = entity_id({"name": source_id or name, "type": etype}, namespace)
        if key not in added_nodes:
            pr = metrics_map.get(key, {}).get("pagerank", 0.005)
            comm = metrics_map.get(key, {}).get("community", "N/A")
            size = max(12, min(65, pr * 1000))
            
            title_html = f"<b>{escape(name)}</b><br>Type: {etype}<br>Source: {namespace}<br>Identifier: {source_id}<br>Community: {comm}<br>PageRank: {pr:.4f}"
            net.add_node(key, label=name, title=title_html, color=get_color(etype), size=size)
            added_nodes.add(key)
        return key

    with open(fused_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            e1 = data["entity_1"]["name"]
            t1 = data["entity_1"].get("type", "Unknown")
            e2 = data["entity_2"]["name"]
            t2 = data["entity_2"].get("type", "Unknown")
            rel = data.get("relation", "")
            
            a = add_node_safe(e1, t1)
            b = add_node_safe(e2, t2)
            
            conf = data.get("computed_confidence", 0.0)
            net.add_edge(a, b, title=f"Relation: {rel}<br>Heuristic score (not accuracy): {conf}", label=rel, physics=True)

    ot_file = Path(args.opentargets_file)
    if ot_file.exists():
        with open(ot_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                gene = data["gene_symbol"]
                score = data.get("score", 0.0)
                a = add_node_safe(gene, "Gene", "opentargets", data["target_id"])
                b = add_node_safe(data["disease_id"], "Disease", "opentargets", data["disease_id"])
                net.add_edge(a, b, title=f"Source: Open Targets<br>Association score (not accuracy): {score}", label="ASSOCIATED_WITH", physics=True, color="#bdc3c7")

    out_html = Path(args.output_file)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    
    # PyVis write_html uses the Windows default encoding; bundled JS includes
    # characters outside GBK. Export the generated HTML explicitly as UTF-8.
    out_html.write_text(net.generate_html(), encoding="utf-8")
    strip_trailing_whitespace(out_html)
    logging.info(f"Topological interactive network visualization universally packaged down successfully out to {out_html}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
