from collections import defaultdict


def build_evidence_catalog(context):
    catalog = {}
    records_by_id = {}
    for key in ("aligned_triples", "fused_edges", "graph_neighborhood"):
        for record in context.get(key, []):
            evidence_id = str(record.get("evidence_id", "")).strip()
            if not evidence_id:
                continue
            if key == "aligned_triples":
                pmids = [record.get("source_pmid", "")]
            elif key == "fused_edges":
                pmids = record.get("evidence", {}).get("pmid_list", [])
            else:
                pmids = record.get("evidence_pmids", [])
            catalog[evidence_id] = {
                str(pmid).strip()
                for pmid in pmids
                if str(pmid).strip()
            }
            records_by_id[evidence_id] = (key, record)
    return catalog, records_by_id


def validate_answer_payload(payload, context):
    problems = []
    if not isinstance(payload, dict):
        return ["answer_not_object"]

    claims = payload.get("claims")
    limitations = payload.get("limitations")
    if not isinstance(claims, list):
        problems.append("claims_not_list")
        claims = []
    if not isinstance(limitations, list):
        problems.append("limitations_not_list")
        limitations = []
    elif any(not isinstance(item, str) or not item.strip() for item in limitations):
        problems.append("limitations_invalid")

    try:
        confidence = float(payload.get("confidence"))
        if confidence < 0.0 or confidence > 1.0:
            problems.append("confidence_out_of_range")
    except (TypeError, ValueError):
        problems.append("confidence_invalid")

    allowed_pmids = {
        str(pmid)
        for pmid in context.get("allowed_citation_pmids", context.get("supporting_pmids", []))
    }
    allowed_evidence_ids = set(context.get("allowed_evidence_ids", []))
    evidence_catalog, _ = build_evidence_catalog(context)
    seen_claim_ids = set()

    for index, claim in enumerate(claims, 1):
        prefix = f"claim_{index}"
        if not isinstance(claim, dict):
            problems.append(f"{prefix}_not_object")
            continue
        claim_id = str(claim.get("claim_id", "")).strip()
        text = str(claim.get("text", "")).strip()
        claim_pmids = claim.get("supporting_pmids")
        evidence_ids = claim.get("supporting_evidence_ids")

        if not claim_id:
            problems.append(f"{prefix}_id_empty")
        elif claim_id in seen_claim_ids:
            problems.append(f"{prefix}_id_duplicate")
        else:
            seen_claim_ids.add(claim_id)
        if not text:
            problems.append(f"{prefix}_text_empty")
        if not isinstance(claim_pmids, list) or not claim_pmids:
            problems.append(f"{prefix}_pmids_empty")
            claim_pmids = []
        if not isinstance(evidence_ids, list) or not evidence_ids:
            problems.append(f"{prefix}_evidence_ids_empty")
            evidence_ids = []

        normalized_pmids = [str(pmid).strip() for pmid in claim_pmids if str(pmid).strip()]
        normalized_evidence_ids = [
            str(evidence_id).strip()
            for evidence_id in evidence_ids
            if str(evidence_id).strip()
        ]
        if len(normalized_pmids) != len(claim_pmids):
            problems.append(f"{prefix}_pmid_invalid")
        if len(normalized_evidence_ids) != len(evidence_ids):
            problems.append(f"{prefix}_evidence_id_invalid")

        unauthorized_pmids = sorted(set(normalized_pmids) - allowed_pmids)
        if unauthorized_pmids:
            problems.append(f"{prefix}_pmid_not_allowed:{','.join(unauthorized_pmids)}")
        unknown_evidence_ids = sorted(
            set(normalized_evidence_ids) - allowed_evidence_ids
            | (set(normalized_evidence_ids) - set(evidence_catalog))
        )
        if unknown_evidence_ids:
            problems.append(f"{prefix}_evidence_id_not_allowed:{','.join(unknown_evidence_ids)}")

        valid_evidence_ids = [
            evidence_id
            for evidence_id in normalized_evidence_ids
            if evidence_id in evidence_catalog and evidence_id in allowed_evidence_ids
        ]
        cited_pmids = set(normalized_pmids)
        covered_pmids = set()
        for evidence_id in valid_evidence_ids:
            evidence_pmids = evidence_catalog[evidence_id]
            covered_pmids.update(evidence_pmids)
            if not cited_pmids.intersection(evidence_pmids):
                problems.append(f"{prefix}_evidence_pmid_mismatch:{evidence_id}")
        uncovered_pmids = sorted(cited_pmids - covered_pmids)
        if uncovered_pmids:
            problems.append(f"{prefix}_pmid_not_backed_by_evidence:{','.join(uncovered_pmids)}")

    if claims and (not allowed_pmids or not evidence_catalog):
        problems.append("claims_present_without_available_evidence")
    if not claims and not limitations:
        problems.append("empty_answer_without_limitation")
    if context.get("conflicts") and not limitations:
        problems.append("conflict_not_disclosed")

    return list(dict.fromkeys(problems))


def build_validated_answer(question, payload, context, model, attempts):
    _, records_by_id = build_evidence_catalog(context)
    claims = []
    supporting_pmids = []
    referenced_ids = []
    for claim in payload.get("claims", []):
        claim_pmids = list(dict.fromkeys(str(pmid) for pmid in claim["supporting_pmids"]))
        evidence_ids = list(dict.fromkeys(str(item) for item in claim["supporting_evidence_ids"]))
        claims.append({
            "claim_id": str(claim["claim_id"]),
            "text": str(claim["text"]).strip(),
            "supporting_pmids": claim_pmids,
            "supporting_evidence_ids": evidence_ids,
        })
        supporting_pmids.extend(claim_pmids)
        referenced_ids.extend(evidence_ids)

    supporting_pmids = list(dict.fromkeys(supporting_pmids))
    referenced_ids = list(dict.fromkeys(referenced_ids))
    grouped_records = defaultdict(list)
    for evidence_id in referenced_ids:
        key, record = records_by_id[evidence_id]
        grouped_records[key].append(record)

    answer_parts = []
    for claim in claims:
        citations = ", ".join(claim["supporting_pmids"])
        answer_parts.append(f"{claim['text']} [PMID: {citations}]")
    limitations = [str(item).strip() for item in payload.get("limitations", []) if str(item).strip()]
    if answer_parts:
        answer = " ".join(answer_parts)
        status = "validated"
    else:
        answer = limitations[0] if limitations else "The supplied evidence is insufficient for a supported answer."
        status = "insufficient_evidence"

    return {
        "question": question,
        "answer_status": status,
        "answer": answer,
        "claims": claims,
        "supporting_pmids": supporting_pmids,
        "supporting_triples": grouped_records["aligned_triples"],
        "graph_context": grouped_records["fused_edges"],
        "graph_neighborhood": grouped_records["graph_neighborhood"],
        "limitations": limitations,
        "confidence": float(payload["confidence"]),
        "model": model,
        "retrieval": context.get("retrieval", {}),
        "validation": {
            "passed": True,
            "attempts": attempts,
            "violations": [],
        },
    }


def build_safe_fallback_answer(question, context, model, attempts, violations):
    return {
        "question": question,
        "answer_status": "insufficient_or_invalid_evidence",
        "answer": "The supplied evidence could not produce a citation-validated answer.",
        "claims": [],
        "supporting_pmids": [],
        "supporting_triples": [],
        "graph_context": [],
        "graph_neighborhood": [],
        "limitations": ["Model output failed evidence validation."],
        "confidence": 0.0,
        "model": model,
        "retrieval": context.get("retrieval", {}),
        "validation": {
            "passed": False,
            "attempts": attempts,
            "violations": list(violations),
        },
    }
