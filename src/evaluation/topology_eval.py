import os

from neo4j import GraphDatabase

def main():
    print("==================================================")
    print("   GRAPH TOPOLOGY EVALUATION REPORT")
    print("==================================================")

    uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', 'testpassword')

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        print(f"Failed to connect to Neo4j at {uri}: {e}")
        return

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
            
            print(f"Graph Topology Evaluation:")
            print(f" - Total Nodes: {total_nodes}")
            print(f" - Average Node Degree: {avg_degree:.2f}")
            print(f" - Isolated Nodes Ratio: {isolated_ratio:.2%}\n")
            
    except Exception as e:
        print(f"Error querying Neo4j: {e}")
    finally:
        driver.close()

    print("==================================================")

if __name__ == "__main__":
    main()
