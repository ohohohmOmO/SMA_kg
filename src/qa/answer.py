import json
import os

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.extraction.llm_extractor import build_client, load_local_env
from src.qa.answer_validation import (
    build_safe_fallback_answer,
    build_validated_answer,
    validate_answer_payload,
)
from src.qa.claim_evidence_validation import validate_answer_semantics
from src.qa.entailment_judge import LLMEntailmentJudge
from src.qa.retriever import context_to_prompt


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"

SYSTEM_PROMPT = """
You answer questions about the SMA knowledge graph using ONLY the supplied
Evidence Context. Do not use outside biomedical knowledge.

Return ONLY valid JSON with this shape:
{
  "claims": [
    {
      "claim_id": "C001",
      "claim_type": "diagnosis|treatment|dosage|contraindication|safety|prognosis|mechanism|association|other",
      "text": "one short evidence-grounded claim",
      "supporting_pmids": ["PMID"],
      "supporting_evidence_ids": ["T001"]
    }
  ],
  "limitations": [],
  "confidence": 0.0
}

Rules:
1. Every claim MUST cite at least one PMID from allowed_citation_pmids.
2. Every claim MUST cite at least one ID from allowed_evidence_ids.
3. A cited PMID MUST belong to at least one cited evidence ID.
4. If evidence is insufficient, return an empty claims list and explain why in limitations.
5. If Evidence Context contains conflicts, disclose the disagreement in limitations.
6. Do not invent mechanisms, treatments, outcomes, PMIDs, or evidence IDs.
7. Keep every claim atomic: one subject, one relation, and one outcome.
"""


def build_dry_run_answer(question, context):
    return {
        "question": question,
        "answer_status": "dry_run_requires_llm",
        "answer": "",
        "claims": [],
        "supporting_pmids": context.get("supporting_pmids", []),
        "supporting_triples": context.get("aligned_triples", [])[:8],
        "graph_context": context.get("fused_edges", [])[:8],
        "graph_neighborhood": context.get("graph_neighborhood", [])[:8],
        "limitations": ["dry_run: no LLM answer generated"],
        "model": "",
        "retrieval": context.get("retrieval", {}),
        "validation": {
            "passed": False,
            "attempts": 0,
            "violations": ["dry_run_no_llm_answer"],
        },
        "evidence_context": context,
    }


def generate_answer(
    question,
    context,
    model=DEFAULT_MODEL,
    max_tokens=1024,
    validation_attempts=2,
    semantic_validation_mode="enforce",
    entailment_judge=None,
    entailment_attempts=3,
):
    load_local_env()
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("SILICONFLOW_API_KEY is not set; use --dry-run to inspect retrieved evidence.")
    client = build_client(api_key)
    semantic_judge = entailment_judge
    if semantic_judge is None and semantic_validation_mode != "off":
        semantic_judge = LLMEntailmentJudge(
            client,
            model=model,
            attempts=entailment_attempts,
        )
    attempts = max(1, int(validation_attempts))
    violations = []
    semantic_validation = None
    for attempt in range(1, attempts + 1):
        try:
            raw = call_llm(
                client,
                question,
                context,
                model,
                max_tokens,
                validation_errors=violations,
            )
        except Exception as exc:
            violations = [f"llm_call_failed:{type(exc).__name__}"]
            return build_safe_fallback_answer(question, context, model, attempt, violations)
        try:
            data = json.loads(clean_json_text(raw))
        except json.JSONDecodeError:
            violations = ["answer_json_invalid"]
            continue
        violations = validate_answer_payload(data, context)
        if not violations:
            semantic_validation = validate_answer_semantics(
                data,
                context,
                judge=semantic_judge,
                mode=semantic_validation_mode,
            )
            violations = (
                []
                if semantic_validation["passed"]
                else list(semantic_validation["violations"])
            )
        if not violations:
            return build_validated_answer(
                question,
                data,
                context,
                model,
                attempt,
                semantic_validation=semantic_validation,
            )
    return build_safe_fallback_answer(
        question,
        context,
        model,
        attempts,
        violations,
        semantic_validation=semantic_validation,
    )


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(Exception),
)
def call_llm(client, question, context, model, max_tokens, validation_errors=None):
    correction = ""
    if validation_errors:
        correction = (
            "\nYour previous answer failed local validation. Regenerate the complete JSON object and fix "
            f"these violations: {json.dumps(validation_errors, ensure_ascii=False)}"
        )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\nEvidence Context:\n{context_to_prompt(context)}"
                    f"{correction}"
                ),
            },
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
