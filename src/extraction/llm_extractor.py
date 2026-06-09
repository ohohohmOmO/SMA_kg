import json
import logging
import pandas as pd
import argparse
import os
import sys
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.biomedical.confidence import normalize_and_score

import openai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
      "entity_2": {"name": "motor function", "type": "Phenotype"},
      "evidence_text": "Zolgensma treatment significantly improves motor function",
      "confidence": 0.92
    }
  ]
}

CRITICAL RULES:
1. You MUST output ONLY valid JSON format.
2. DO NOT include any conversational text, greetings, explanations, or preambles.
3. DO NOT wrap the output in markdown blocks (e.g., no ```json).
4. If there are no relevant triples, output exactly: {"triples": []}
5. Entity type MUST be one of: Gene, Protein, Phenotype, Drug, Disease, Variant.
6. Relation MUST be one of: ASSOCIATED_WITH, TREATS, IMPROVES, WORSENS, CAUSES,
   DECREASES, INCREASES, REGULATES, TARGETS, PREVENTS, HAS_VARIANT,
   HAS_PHENOTYPE, BIOMARKER_FOR, DIAGNOSES, EXPRESSED_IN, ADMINISTERED_BY,
   ENCODES, MODELS, CO_OCCURS_WITH, COMPARED_WITH, USED_IN, NO_EFFECT.
7. evidence_text MUST be a short exact quote or close span from the abstract
   supporting the triple.
8. confidence MUST be a calibrated self-score from 0.0 to 1.0 based on explicit
   textual evidence, not general biomedical plausibility.
"""

def load_local_env():
    """Load local secrets without requiring python-dotenv."""
    for env_file in (Path(".env"), Path(".env.local")):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def build_client(api_key):
    return openai.OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        timeout=60.0,
    )

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception)
)
def call_llm_extraction(client, abstract_text, pmid, model, max_tokens):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"PMID: {pmid}\nAbstract: {abstract_text}"}
        ],
        temperature=0.0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content

def parse_args():
    parser = argparse.ArgumentParser(description="Extract biomedical triples with a SiliconFlow LLM.")
    parser.add_argument("--input-file", default="data/raw/pubmed_sma_abstracts.jsonl")
    parser.add_argument("--output-file", default="data/processed/llm_extracted_triples.jsonl")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V4-Flash")
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--min-triples", type=int, default=1)
    parser.add_argument("--rejected-file", default="")
    return parser.parse_args()

def main():
    load_local_env()
    args = parse_args()
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        logging.error("SILICONFLOW_API_KEY is not set. Refusing to run LLM extraction.")
        return 1

    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_output_file = output_file.with_name(f"{output_file.name}.tmp")
    rejected_file = Path(args.rejected_file) if args.rejected_file else output_file.with_name(f"{output_file.name}.rejected.jsonl")
    rejected_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        logging.error(f"Input file {input_file} not found.")
        return 1

    client = build_client(api_key)
    stop = None if args.limit < 0 else args.offset + args.limit
    df = pd.read_json(input_file, lines=True).iloc[args.offset:stop]
    successful_triples = 0
    rejected_triples = 0
    malformed_outputs = 0
    failed_records = 0

    with open(temp_output_file, 'w', encoding='utf-8') as f, open(rejected_file, 'w', encoding='utf-8') as rejected:
        for idx, row in df.iterrows():
            pmid = str(row.get("pmid", ""))
            abstract = row.get("abstract", "")
            if not abstract: continue
                
            try:
                result_json_str = call_llm_extraction(client, abstract, pmid, args.model, args.max_tokens)
                
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
                    malformed_outputs += 1
                    logging.warning(
                        "Malformed JSON for PMID %s. Skipping. Error: %s. Raw output preview: %s",
                        pmid,
                        e,
                        cleaned_str[:500],
                    )
                    continue
                
                for triple in result_data.get("triples", []):
                    raw_triple = {
                        "source_pmid": pmid,
                        "entity_1": triple.get("entity_1", {}),
                        "relation": triple.get("relation", ""),
                        "entity_2": triple.get("entity_2", {}),
                        "evidence_text": triple.get("evidence_text", ""),
                        "llm_confidence": triple.get("confidence"),
                        "extracted_by": f"LLM_{args.model}"
                    }
                    unified_triple, problems = normalize_and_score(raw_triple, require_evidence=True)
                    if problems:
                        rejected.write(json.dumps({
                            "source_pmid": pmid,
                            "problems": problems,
                            "record": raw_triple,
                        }, ensure_ascii=False) + "\n")
                        rejected_triples += 1
                        continue
                    f.write(json.dumps(unified_triple, ensure_ascii=False) + "\n")
                    successful_triples += 1
            except Exception as e:
                failed_records += 1
                logging.warning(f"Failed to process PMID {pmid} (API or logic error): {e}")

    if successful_triples < args.min_triples:
        logging.error(
            "LLM extraction produced %s triples, below min_triples=%s. Keeping existing output file untouched.",
            successful_triples,
            args.min_triples,
        )
        temp_output_file.unlink(missing_ok=True)
        return 1

    temp_output_file.replace(output_file)
    logging.info(
        "LLM Extraction complete. Extracted %s triples to %s. malformed_outputs=%s failed_records=%s",
        successful_triples,
        output_file,
        malformed_outputs,
        failed_records,
    )
    logging.info("Rejected %s invalid LLM triples to %s.", rejected_triples, rejected_file)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
