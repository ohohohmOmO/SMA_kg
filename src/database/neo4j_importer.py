import argparse
import os
import json
import logging
from pathlib import Path
import sys
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.schema import normalize_entity_type, normalize_relation, relation_key

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


SAFE_CYPHER_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_label(raw_type):
    label = normalize_entity_type(raw_type) or "Unknown"
    if not SAFE_CYPHER_TOKEN.match(label):
        return "Unknown"
    return label


def safe_relationship_type(raw_relation):
    rel = normalize_relation(raw_relation) or "ASSOCIATED_WITH"
    if not SAFE_CYPHER_TOKEN.match(rel):
        return "ASSOCIATED_WITH"
    return rel

class Neo4jImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def verify_connectivity(self):
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def setup_constraints(self):
        # Enforce unique entity names natively spanning graph tags
        query = "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE"
        with self.driver.session() as session:
            session.run(query)
            logging.info("Unique constraint on Entity.name established.")

    def clear_managed_graph(self):
        with self.driver.session() as session:
            rel_result = session.run(
                """
                MATCH ()-[r]->()
                WHERE r.source IN ['OpenTargets', 'Literature_NLP']
                WITH collect(r) AS rels, count(r) AS rel_count
                FOREACH (rel IN rels | DELETE rel)
                RETURN rel_count
                """
            ).single()
            node_result = session.run(
                """
                MATCH (n:Entity)
                WHERE n.kg_sma_managed = true OR NOT (n)--()
                WITH collect(n) AS nodes, count(n) AS node_count
                FOREACH (node IN nodes | DETACH DELETE node)
                RETURN node_count
                """
            ).single()
        rel_count = rel_result["rel_count"] if rel_result else 0
        node_count = node_result["node_count"] if node_result else 0
        logging.info("Cleared %s managed relationships and %s managed/orphan Entity nodes.", rel_count, node_count)
        return {"relationships_deleted": rel_count, "nodes_deleted": node_count}

    def import_open_targets(self, filepath):
        if not Path(filepath).exists():
            logging.warning(f"{filepath} not found. Skipping Open Targets import.")
            return 0

        query = """
        MERGE (disease:Entity:Disease {name: trim($disease_name)})
        SET disease.kg_sma_managed = true
        MERGE (gene:Entity:Gene {name: trim($gene_symbol)})
        SET gene.kg_sma_managed = true
        MERGE (gene)-[r:ASSOCIATED_WITH]->(disease)
        SET r.score = toFloat($score),
            r.source = 'OpenTargets'
        """

        count = 0
        with self.driver.session() as session:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    session.run(query, 
                                disease_name="Spinal Muscular Atrophy", # Standardizing universally
                                gene_symbol=data["gene_symbol"], 
                                score=data.get("score", 0.0))
                    count += 1
        logging.info(f"Imported {count} Open Targets baseline associations.")
        return count

    def import_fused_triples(self, filepath):
        if not Path(filepath).exists():
            logging.warning(f"{filepath} not found. Skipping combined literature import.")
            return 0

        count = 0
        with self.driver.session() as session:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)

                    e1_name = data.get("entity_1", {}).get("name", "Unknown")
                    e1_type = safe_label(data.get("entity_1", {}).get("type", "Unknown"))
                    e2_name = data.get("entity_2", {}).get("name", "Unknown")
                    e2_type = safe_label(data.get("entity_2", {}).get("type", "Unknown"))
                    
                    rel_type = safe_relationship_type(data.get("relation", "ASSOCIATED_WITH"))
                    conf = data.get("computed_confidence", 0.0)
                    evidence = data.get("evidence", {})
                    pmids = evidence.get("pmid_list", [])

                    # Dynamic Cypher query injection securely resolving relation tags directly without APOC dependency
                    query = f"""
                    MERGE (e1:Entity {{name: trim($e1_name)}})
                    SET e1:{e1_type},
                        e1.kg_sma_managed = true
                    MERGE (e2:Entity {{name: trim($e2_name)}})
                    SET e2:{e2_type},
                        e2.kg_sma_managed = true
                    MERGE (e1)-[r:{rel_type}]->(e2)
                    SET r.confidence = toFloat($confidence),
                        r.evidence_pmids = $pmids,
                        r.source = 'Literature_NLP',
                        r.review_status = $review_status
                    """
                    
                    try:
                        session.run(query, 
                                    e1_name=e1_name, 
                                    e2_name=e2_name, 
                                    confidence=conf, 
                                    pmids=pmids,
                                    review_status=data.get("review_status", "accepted"))
                        count += 1
                    except Exception as e:
                        logging.error(f"Failed to insert triple bounds: {e1_name} -> {rel_type} -> {e2_name}. Error: {e}")

        logging.info(f"Imported {count} fused literature triples tightly aligned to constraints.")
        return count

def parse_args():
    parser = argparse.ArgumentParser(description="Import SMA KG outputs into Neo4j.")
    parser.add_argument("--fused-file", default="data/processed/fused_triples.jsonl")
    parser.add_argument("--opentargets-file", default="data/external/sma_gda_baseline.jsonl")
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--clear-managed-graph", action="store_true")
    return parser.parse_args()

def main():
    args = parse_args()
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    importer = Neo4jImporter(uri, user, password)
    summary = {
        "uri": uri,
        "user": user,
        "fused_file": args.fused_file,
        "opentargets_file": args.opentargets_file,
        "clear_managed_graph": args.clear_managed_graph,
        "managed_clear": {},
        "open_targets_imported": 0,
        "fused_triples_imported": 0,
    }
    try:
        importer.verify_connectivity()
        importer.setup_constraints()
        if args.clear_managed_graph:
            summary["managed_clear"] = importer.clear_managed_graph()
        summary["open_targets_imported"] = importer.import_open_targets(args.opentargets_file)
        summary["fused_triples_imported"] = importer.import_fused_triples(args.fused_file)
        logging.info("Neo4j Graph Database structural arrays successfully deployed.")
    finally:
        importer.close()
    if args.summary_file:
        summary_path = Path(args.summary_file)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
