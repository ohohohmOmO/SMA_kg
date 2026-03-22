import json
import logging
import pandas as pd
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

try:
    import openai
except ImportError:
    import subprocess; import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    import openai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import os
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY")
if not SILICONFLOW_API_KEY:
    logging.warning("SILICONFLOW_API_KEY is not set. API calls will fail.")

client = openai.OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)

SYSTEM_PROMPT = """
You are an expert biomedical NLP extraction engine.
Analyze the provided text and perform Named Entity Recognition (NER) and Relation Extraction (RE).
Only extract interactions explicitly focused on Genes, Proteins, Phenotypes, and Drugs related directly to SMA.

Example Input: "Zolgensma treatment significantly improves motor function in spinal muscular atrophy trials."
Example Output Format:
{
  "triples": [
    {
      "entity_1": {"name": "Zolgensma", "type": "Drug"},
      "relation": "IMPROVES",
      "entity_2": {"name": "motor function", "type": "Phenotype"}
    }
  ]
}

CRITICAL RULES:
1. You MUST output ONLY valid JSON format.
2. DO NOT include any conversational text, greetings, explanations, or preambles.
3. DO NOT wrap the output in markdown blocks (e.g., no ```json).
4. If there are no relevant triples, output exactly: {"triples": []}
"""

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception)
)
def call_llm_extraction(abstract_text, pmid):
    if not SILICONFLOW_API_KEY:
        raise ValueError("SILICONFLOW_API_KEY is missing.")

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"PMID: {pmid}\nAbstract: {abstract_text}"}
        ],
        temperature=0.0
    )
    return response.choices[0].message.content

def main():
    input_file = Path("data/raw/pubmed_sma_abstracts.jsonl")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "llm_extracted_triples.jsonl"

    if not input_file.exists():
        logging.error(f"Input file {input_file} not found.")
        return

    df = pd.read_json(input_file, lines=True).head(200)
    successful_triples = 0
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            pmid = str(row.get("pmid", ""))
            abstract = row.get("abstract", "")
            if not abstract: continue
                
            try:
                result_json_str = call_llm_extraction(abstract, pmid)
                
                # Cleanup potential markdown wrapper just in case the LLM disobeys
                cleaned_str = result_json_str.strip()
                if cleaned_str.startswith("```json"):
                    cleaned_str = cleaned_str[7:]
                elif cleaned_str.startswith("```"):
                    cleaned_str = cleaned_str[3:]
                if cleaned_str.endswith("```"):
                    cleaned_str = cleaned_str[:-3]
                cleaned_str = cleaned_str.strip()
                
                try:
                    result_data = json.loads(cleaned_str)
                except json.JSONDecodeError as e:
                    logging.warning(f"Malformed JSON for PMID {pmid}. Skipping. Error: {e}\nRaw output: {cleaned_str}")
                    continue
                
                for triple in result_data.get("triples", []):
                    unified_triple = {
                        "source_pmid": pmid,
                        "entity_1": triple.get("entity_1", {}),
                        "relation": triple.get("relation", ""),
                        "entity_2": triple.get("entity_2", {}),
                        "computed_confidence": 0.90,
                        "extracted_by": "LLM_Qwen2.5_7B"
                    }
                    f.write(json.dumps(unified_triple) + "\n")
                    successful_triples += 1
            except Exception as e:
                logging.warning(f"Failed to process PMID {pmid} (API or logic error): {e}")
                
    logging.info(f"LLM Extraction complete. Extracted {successful_triples} triples to {output_file}.")

if __name__ == "__main__":
    main()
