import json
import logging
import sys
import subprocess
from pathlib import Path

try:
    import requests
    from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "tenacity"])
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
def fetch_page(variables):
    """Fetch a single page from Open Targets API with exponential backoff retries."""
    response = requests.post(
        API_URL,
        json={"query": QUERY_STRING, "variables": variables},
        timeout=30,
        verify=False
    )
    if not response.ok:
        logging.error(f"GraphQL Error Response: {response.text}")
    response.raise_for_status()
    return response.json()

def fetch_opentargets_gda(disease_id: str = "MONDO_0009669"):
    """Iterate through pages to fetch all associated targets for a given disease ID."""
    logging.info(f"Fetching Open Targets data for {disease_id}...")
    all_rows = []
    
    index = 0
    size = 1000
    
    while True:
        variables = {"diseaseId": disease_id, "page": {"index": index, "size": size}}
        
        response = fetch_page(variables)
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

def main():
    output_dir = Path("data/external")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "sma_gda_baseline.jsonl"
    
    try:
        data = fetch_opentargets_gda()
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
        
    except Exception as e:
        logging.exception(f"Failed to fetch or process data: {e}")

if __name__ == "__main__":
    main()
