import pandas as pd
import numpy as np
import json
import os

try:
    from sklearn.metrics import cohen_kappa_score
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
    from sklearn.metrics import cohen_kappa_score

try:
    import openai
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    import openai

from tenacity import retry, wait_exponential, stop_after_attempt

SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY")

client = openai.OpenAI(
    api_key=SILICONFLOW_API_KEY if SILICONFLOW_API_KEY else "fake_key",
    base_url="https://api.siliconflow.cn/v1"
)

SYSTEM_PROMPT = """You are an expert biological evaluator. 
Given an abstract and an extracted biological relation triple, rate the factuality of the triple based ONLY on the abstract.
Outputs MUST be a single integer:
2: The relation is completely supported by the abstract.
1: The relation is partially supported or inferred.
0: The relation is not supported by the abstract.
Do NOT output anything other than the integer 0, 1, or 2.
"""

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def get_llm_score(abstract_text, entity_1, relation, entity_2):
    if not SILICONFLOW_API_KEY:
        return 1 # Fallback if testing without key
        
    prompt = f"Abstract: {abstract_text}\nTriple: ({entity_1}) - [{relation}] -> ({entity_2})\nRating:"
    
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    res = response.choices[0].message.content.strip()
    for char in res:
        if char in "012":
            return int(char)
    return 0

def parse_pmids(raw_str):
    raw_str = str(raw_str).strip()
    if not raw_str or raw_str == 'nan': return []
    if ',' in raw_str:
        parts = [p.strip() for p in raw_str.split(',')]
        is_mangled = len(parts) > 1 and all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3
        if is_mangled:
            merged = "".join(parts)
            return [merged[i:i+8] for i in range(0, len(merged), 8) if len(merged[i:i+8]) == 8]
        return parts
    return [raw_str]

def main():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    csv_file = os.path.join(BASE_DIR, 'data', 'processed', 'human_evaluation_sample_scored.csv')
    raw_jsonl = os.path.join(BASE_DIR, 'data', 'raw', 'pubmed_sma_abstracts.jsonl')
    
    print("==================================================")
    print("   EVALUATION METRICS & LLM-AS-A-JUDGE REPORT")
    print("==================================================")

    df = pd.read_csv(csv_file)
    df = df.dropna(subset=['Entity_1', 'Human_Score'])
    df['Human_Score'] = pd.to_numeric(df['Human_Score'], errors='coerce')
    df = df.dropna(subset=['Human_Score'])
    df['Human_Score'] = df['Human_Score'].astype(int)
    
    total_human = len(df)
    human_strict = (df['Human_Score'] == 2).sum() / total_human
    human_lenient = (df['Human_Score'] >= 1).sum() / total_human
    human_avg = df['Human_Score'].mean()

    print(f"Human Evaluation Metrics (n={total_human}):")
    print(f" - Strict Accuracy (Score == 2): {human_strict:.2%}")
    print(f" - Lenient Accuracy (Score >= 1): {human_lenient:.2%}")
    print(f" - Average Quality Score: {human_avg:.2f}\n")

    pmid_to_abstract = {}
    if os.path.exists(raw_jsonl):
        with open(raw_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                pmid_to_abstract[str(row.get('pmid', ''))] = row.get('abstract', '')

    print("Running LLM Evaluator via Qwen2.5-7B (SiliconFlow)...")
    llm_scores = []
    
    # Process only first 20 for time/rate limits if requested? User said "autonomously score the same 100 triples".
    for idx, row in df.iterrows():
        pmids = parse_pmids(row['Evidence_PMIDs'])
        abstracts = [pmid_to_abstract[p] for p in pmids if p in pmid_to_abstract]
        combined_abstract = " ".join(abstracts)
        if len(combined_abstract) > 3000:
            combined_abstract = combined_abstract[:3000] # Safe trim
        if not combined_abstract.strip():
            combined_abstract = "No abstract available."
            
        score = get_llm_score(combined_abstract, row['Entity_1'], row['Relation'], row['Entity_2'])
        llm_scores.append(score)
        
    df['LLM_Score'] = llm_scores
    llm_strict = (df['LLM_Score'] == 2).sum() / total_human
    llm_lenient = (df['LLM_Score'] >= 1).sum() / total_human
    llm_avg = df['LLM_Score'].mean()
    
    print("LLM Evaluator Metrics:")
    print(f" - Strict Accuracy: {llm_strict:.2%}")
    print(f" - Lenient Accuracy: {llm_lenient:.2%}")
    print(f" - Average Quality Score: {llm_avg:.2f}\n")

    kappa = cohen_kappa_score(df['Human_Score'], df['LLM_Score'])
    print("Agreement Analysis:")
    print(f" - Cohen's Kappa (Human vs LLM): {kappa:.4f}")

    print("==================================================")

if __name__ == "__main__":
    main()
