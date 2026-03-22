import io
import json
import time
import logging
import sys
import subprocess
from pathlib import Path
from urllib.error import HTTPError

try:
    from Bio import Entrez, Medline
    from tqdm import tqdm
    from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "biopython", "tqdm", "tenacity", "requests"])
    from Bio import Entrez, Medline
    from tqdm import tqdm
    from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# It's important to provide a valid email when using NCBI E-utilities
Entrez.email = "kg_sma_builder@example.com"
Entrez.tool = "SMA_Knowledge_Graph_Data_Miner"

SEARCH_QUERY = '"Spinal Muscular Atrophy"[Title/Abstract]'
RETMAX = 5000
BATCH_SIZE = 200

@retry(
    wait=wait_exponential(multiplier=2, min=4, max=30),
    stop=stop_after_attempt(10),
    retry=retry_if_exception_type(Exception)
)
def fetch_pmids(query, retmax=5000):
    logging.info(f"Searching PubMed for: {query}")
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax)
    record = Entrez.read(handle)
    handle.close()
    return record.get("IdList", [])

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception)
)
def fetch_abstracts_batch(pmid_list):
    handle = Entrez.efetch(db="pubmed", id=",".join(pmid_list), rettype="medline", retmode="text")
    records = handle.read()
    handle.close()
    return records

def parse_medline_records(raw_text):
    records = Medline.parse(io.StringIO(raw_text))
    parsed_data = []
    
    for record in records:
        if "AB" in record: # Enforce only parsing records that have an abstract
            pub_date = record.get("DP", "")
            parsed_data.append({
                "pmid": record.get("PMID", ""),
                "title": record.get("TI", ""),
                "abstract": record.get("AB", ""),
                "pub_date": pub_date
            })
    return parsed_data

def main():
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "pubmed_sma_abstracts.jsonl"
    
    try:
        pmids = fetch_pmids(SEARCH_QUERY, retmax=RETMAX)
        logging.info(f"Found {len(pmids)} PMIDs.")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i in tqdm(range(0, len(pmids), BATCH_SIZE), desc="Fetching pubmed batches"):
                batch_pmids = pmids[i:i+BATCH_SIZE]
                raw_text = fetch_abstracts_batch(batch_pmids)
                
                parsed_records = parse_medline_records(raw_text)
                for rec in parsed_records:
                    f.write(json.dumps(rec) + "\n")
                    
                # Explicit delay to respect the NCBI public baseline limit
                time.sleep(0.35)
                
        logging.info(f"Finished extracting abstracts. Saved to {output_file}")
        
    except Exception as e:
        logging.exception(f"Crawler failed to execute: {e}")

if __name__ == "__main__":
    main()
