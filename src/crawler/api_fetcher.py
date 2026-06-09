import argparse
import json
import logging
from pathlib import Path

import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_URL = "https://api.platform.opentargets.org/api/v4/graphql"

QUERY_STRING = """
query associatedTargets($diseaseId: String!, $page: Pagination) {
  disease(efoId: $diseaseId) {
    id
    name
    associatedTargets(page: $page) {
      count
      rows {
        target {
          id
          approvedSymbol
        }
        score
      }
    }
  }
}
"""

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def fetch_page(variables, verify_tls=True):
    """Fetch a single page from Open Targets API with exponential backoff retries."""
    response = requests.post(
        API_URL,
        json={"query": QUERY_STRING, "variables": variables},
        timeout=30,
        verify=verify_tls
    )
    if not response.ok:
        logging.error(f"GraphQL Error Response: {response.text}")
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise ValueError(f"Open Targets GraphQL errors: {json.dumps(payload['errors'])}")
    return payload

def fetch_opentargets_gda(disease_id: str = "MONDO_0009669", verify_tls=True):
    """Iterate through pages to fetch all associated targets for a given disease ID."""
    logging.info(f"Fetching Open Targets data for {disease_id}...")
    all_rows = []
    
    index = 0
    size = 1000
    
    while True:
        variables = {"diseaseId": disease_id, "page": {"index": index, "size": size}}
        
        response = fetch_page(variables, verify_tls=verify_tls)
        disease_node = response.get("data", {}).get("disease")
        
        if not disease_node:
            logging.warning(f"No disease node found. Response was: {json.dumps(response)}")
            break
            
        associated_targets = disease_node.get("associatedTargets", {})
        rows = associated_targets.get("rows", [])
        
        if not rows:
            break
            
        all_rows.extend(rows)
        logging.info(f"Fetched {len(all_rows)}/{associated_targets.get('count', '?')} associations...")
        
        if len(rows) < size:
            break
            
        index += 1
        
    return {"id": disease_node.get("id") if disease_node else disease_id, "rows": all_rows}

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch SMA gene-disease associations from Open Targets.")
    parser.add_argument("--disease-id", default="MONDO_0009669")
    parser.add_argument("--output-file", default="data/external/sma_gda_baseline.jsonl")
    parser.add_argument("--allow-insecure-tls", action="store_true")
    return parser.parse_args()

def main():
    args = parse_args()
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        data = fetch_opentargets_gda(args.disease_id, verify_tls=not args.allow_insecure_tls)
        disease_id = data.get("id", "EFO_0000109")
        rows = data.get("rows", [])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for row in rows:
                target = row.get("target", {})
                record = {
                    "disease_id": disease_id,
                    "gene_symbol": target.get("approvedSymbol"),
                    "target_id": target.get("id"),
                    "score": row.get("score")
                }
                f.write(json.dumps(record) + "\n")
                
        logging.info(f"Successfully saved {len(rows)} associations to {output_file}")
        return 0
        
    except Exception as e:
        logging.exception(f"Failed to fetch or process data: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
