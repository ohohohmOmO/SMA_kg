import json
import os

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.extraction.llm_extractor import build_client, load_local_env
from src.qa.retriever import context_to_prompt


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"

SYSTEM_PROMPT = """
You answer questions about the SMA knowledge graph using ONLY the supplied
Evidence Context. Do not use outside biomedical knowledge.

Return ONLY valid JSON with this shape:
{
  "answer": "short answer grounded in the evidence",
  "supporting_pmids": ["PMID"],
  "supporting_triples": [],
  "graph_context": [],
  "limitations": [],
  "confidence": 0.0
}

Rules:
1. Cite only PMIDs present in Evidence Context.
2. If the evidence is insufficient, say so in answer and limitations.
3. Do not invent mechanisms, treatments, or outcomes outside the context.
"""


def build_dry_run_answer(question, context):
    return {
        "question": question,
        "answer_status": "dry_run_requires_llm",
        "answer": "",
        "supporting_pmids": context.get("supporting_pmids", []),
        "supporting_triples": context.get("aligned_triples", [])[:8],
        "graph_context": context.get("fused_edges", [])[:8],
        "limitations": ["dry_run: no LLM answer generated"],
        "model": "",
        "retrieval": context.get("retrieval", {}),
        "evidence_context": context,
    }


def generate_answer(question, context, model=DEFAULT_MODEL, max_tokens=1024):
    load_local_env()
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("SILICONFLOW_API_KEY is not set; use --dry-run to inspect retrieved evidence.")
    client = build_client(api_key)
    raw = call_llm(client, question, context, model, max_tokens)
    data = json.loads(clean_json_text(raw))
    data["question"] = question
    data["model"] = model
    data["retrieval"] = context.get("retrieval", {})
    return data


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(Exception),
)
def call_llm(client, question, context, model, max_tokens):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\nEvidence Context:\n{context_to_prompt(context)}"},
        ],
        temperature=0.0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def clean_json_text(raw_text):
    cleaned = str(raw_text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()
