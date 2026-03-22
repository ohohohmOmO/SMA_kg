import json
import logging
import re
import pandas as pd
from pathlib import Path
import sys
import subprocess

try:
    import spacy
    from spacy.matcher import Matcher
    HAS_SPACY = True
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "spacy"])
    import spacy
    from spacy.matcher import Matcher
    HAS_SPACY = True

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DRUGS = ["nusinersen", "risdiplam", "zolgensma", "spinraza", "evrysdi", "onasemnogene abeparvovec"]
GENES = ["smn1", "smn2", "smn", "exon 7"]
DISEASES = ["spinal muscular atrophy", "sma"]

def regex_fallback_extraction(text, pmid):
    triples = []
    text_lower = text.lower()
    for drug in DRUGS:
        if drug in text_lower:
            for disease in DISEASES:
                if disease in text_lower:
                    triples.append({
                        "source_pmid": pmid,
                        "entity_1": {"name": drug.capitalize(), "type": "Drug"},
                        "relation": "TREATS_MENTION",
                        "entity_2": {"name": "SMA", "type": "Disease"},
                        "computed_confidence": 0.75,
                        "extracted_by": "Regex_Fallback"
                    })
    for gene in GENES:
        if gene in text_lower:
            for disease in DISEASES:
                if disease in text_lower:
                    triples.append({
                        "source_pmid": pmid,
                        "entity_1": {"name": gene.upper(), "type": "Gene"},
                        "relation": "ASSOCIATED_WITH_MENTION",
                        "entity_2": {"name": "SMA", "type": "Disease"},
                        "computed_confidence": 0.70,
                        "extracted_by": "Regex_Fallback"
                    })
    return triples

def main():
    input_file = Path("data/raw/pubmed_sma_abstracts.jsonl")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "spacy_extracted_triples.jsonl"

    if not input_file.exists():
        logging.error(f"Input file {input_file} not found.")
        return

    df = pd.read_json(input_file, lines=True).iloc[200:]
    
    successful_triples = 0
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            pmid = str(row.get("pmid", ""))
            abstract = row.get("abstract", "")
            if not abstract: continue
                
            triples = regex_fallback_extraction(abstract, pmid)
            seen = set()
            for t in triples:
                sig = f"{t['entity_1']['name']}_{t['relation']}_{t['entity_2']['name']}"
                if sig not in seen:
                    seen.add(sig)
                    f.write(json.dumps(t) + "\n")
                    successful_triples += 1
                    
    logging.info(f"Local NLP Extraction complete. Extracted {successful_triples} triples to {output_file}.")

if __name__ == "__main__":
    main()
