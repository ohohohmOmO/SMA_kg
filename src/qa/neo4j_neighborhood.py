import os

from src.extraction.llm_extractor import load_local_env


def attach_neo4j_neighborhood(context, limit=8):
    try:
        context["graph_neighborhood"] = fetch_neo4j_neighborhood(context.get("entities", []), limit=limit)
        context["graph_neighborhood_error"] = ""
    except Exception as exc:
        context["graph_neighborhood"] = []
        context["graph_neighborhood_error"] = f"{type(exc).__name__}: {exc}"
    return context


def fetch_neo4j_neighborhood(entities, limit=8):
    load_local_env()
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not (uri and user and password):
        raise RuntimeError("Neo4j environment variables are incomplete.")
    from neo4j import GraphDatabase

    names = [{"name": item.get("name", "")} for item in entities if item.get("name")]
    if not names:
        return []
    query = """
    UNWIND $entities AS entity
    MATCH (e:Entity {name: entity.name})
    CALL (e) {
      MATCH (e)-[r]-(n:Entity)
      RETURN type(r) AS relation,
             n.name AS neighbor,
             labels(n) AS neighbor_labels,
             properties(r) AS properties
      ORDER BY coalesce(r.confidence, r.score, 0.0) DESC, n.name
      LIMIT $limit
    }
    RETURN entity.name AS query_entity,
           e.name AS source_entity,
           labels(e) AS source_labels,
           relation,
           neighbor,
           neighbor_labels,
           properties
    """
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            rows = session.run(query, entities=names, limit=max(1, int(limit)))
            return [format_neighbor_record(row.data()) for row in rows]
    finally:
        driver.close()


def format_neighbor_record(row):
    properties = row.get("properties", {}) or {}
    return {
        "query_entity": row.get("query_entity", ""),
        "source_entity": row.get("source_entity", ""),
        "source_labels": sorted(label for label in row.get("source_labels", []) if label != "Entity"),
        "relation": row.get("relation", ""),
        "neighbor": row.get("neighbor", ""),
        "neighbor_labels": sorted(label for label in row.get("neighbor_labels", []) if label != "Entity"),
        "confidence": properties.get("confidence", properties.get("score", 0.0)),
        "source": properties.get("source", ""),
        "review_status": properties.get("review_status", ""),
        "evidence_pmids": properties.get("evidence_pmids", []),
    }
