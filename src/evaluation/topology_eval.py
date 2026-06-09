import argparse
import json
import os

from neo4j import GraphDatabase

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Neo4j graph topology.")
    parser.add_argument("--output-file", default="")
    return parser.parse_args()

def main():
    args = parse_args()
    print("==================================================")
    print("   GRAPH TOPOLOGY EVALUATION REPORT")
    print("==================================================")

    uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', 'testpassword')

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        print(f"Failed to connect to Neo4j at {uri}: {e}")
        return 1

    metrics = {}
    try:
        with driver.session() as session:
            # Total Nodes
            total_nodes_query = "MATCH (n) RETURN count(n) AS total_nodes"
            res = session.run(total_nodes_query).single()
            total_nodes = res['total_nodes'] if res else 0
            
            # Isolated Nodes
            isolated_query = "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS isolated_nodes"
            res = session.run(isolated_query).single()
            isolated_nodes = res['isolated_nodes'] if res else 0
            
            # Average Degree (Sum of Degrees = 2 * Edges)
            rels_query = "MATCH ()-[r]->() RETURN count(r) AS total_rels"
            res = session.run(rels_query).single()
            total_rels = res['total_rels'] if res else 0
            
            avg_degree = (2.0 * total_rels) / total_nodes if total_nodes > 0 else 0.0
            isolated_ratio = (isolated_nodes / total_nodes) if total_nodes > 0 else 0.0
            metrics = {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "average_node_degree": avg_degree,
                "isolated_nodes": isolated_nodes,
                "isolated_nodes_ratio": isolated_ratio,
            }
            
            print(f"Graph Topology Evaluation:")
            print(f" - Total Nodes: {total_nodes}")
            print(f" - Average Node Degree: {avg_degree:.2f}")
            print(f" - Isolated Nodes Ratio: {isolated_ratio:.2%}\n")
            
    except Exception as e:
        print(f"Error querying Neo4j: {e}")
        return 1
    finally:
        driver.close()

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print("==================================================")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
