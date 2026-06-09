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
    rel = normalize_relation(raw_relation) or relation_key(raw_relation) or "ASSOCIATED_WITH"
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

    def import_open_targets(self, filepath):
        if not Path(filepath).exists():
            logging.warning(f"{filepath} not found. Skipping Open Targets import.")
            return

        query = """
        MERGE (disease:Entity:Disease {name: trim($disease_name)})
        MERGE (gene:Entity:Gene {name: trim($gene_symbol)})
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

    def import_fused_triples(self, filepath):
        if not Path(filepath).exists():
            logging.warning(f"{filepath} not found. Skipping combined literature import.")
            return

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
                    SET e1:{e1_type}
                    MERGE (e2:Entity {{name: trim($e2_name)}})
                    SET e2:{e2_type}
                    MERGE (e1)-[r:{rel_type}]->(e2)
                    SET r.confidence = toFloat($confidence),
                        r.evidence_pmids = $pmids,
                        r.source = 'Literature_NLP'
                    """
                    
                    try:
                        session.run(query, 
                                    e1_name=e1_name, 
                                    e2_name=e2_name, 
                                    confidence=conf, 
                                    pmids=pmids)
                        count += 1
                    except Exception as e:
                        logging.error(f"Failed to insert triple bounds: {e1_name} -> {rel_type} -> {e2_name}. Error: {e}")

        logging.info(f"Imported {count} fused literature triples tightly aligned to constraints.")

def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    importer = Neo4jImporter(uri, user, password)
    try:
        importer.setup_constraints()
        importer.import_open_targets("data/external/sma_gda_baseline.jsonl")
        importer.import_fused_triples("data/processed/fused_triples.jsonl")
        logging.info("Neo4j Graph Database structural arrays successfully deployed.")
    finally:
        importer.close()

if __name__ == "__main__":
    main()
