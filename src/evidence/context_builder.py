import re
from collections import Counter, defaultdict

from src.evidence.loaders import load_abstracts_by_pmid, load_jsonl


DEFAULT_LIMITS = {
    "max_abstracts": 8,
    "max_aligned_triples": 24,
    "max_fused_edges": 16,
    "max_conflicts": 8,
    "max_abstract_chars": 1200,
    "max_supporting_pmids": 32,
}


def entity_pair_key(entity_1, entity_2):
    return (
        _clean(entity_1.get("name", "")).lower(),
        _clean(entity_1.get("type", "")),
        _clean(entity_2.get("name", "")).lower(),
        _clean(entity_2.get("type", "")),
    )


def undirected_pair_key(entity_1, entity_2):
    left = (_clean(entity_1.get("name", "")).lower(), _clean(entity_1.get("type", "")))
    right = (_clean(entity_2.get("name", "")).lower(), _clean(entity_2.get("type", "")))
    return tuple(sorted([left, right]))


def tokenize_query(text):
    return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", str(text or ""))]


class EvidenceContextBuilder:
    def __init__(
        self,
        abstracts_file="data/raw/pubmed_sma_abstracts.jsonl",
        aligned_triples_file="data/interim/aligned_triples.jsonl",
        fused_triples_file="data/processed/fused_triples.jsonl",
        conflicts_file="data/interim/relation_conflicts.jsonl",
        limits=None,
    ):
        self.abstracts_file = abstracts_file
        self.aligned_triples_file = aligned_triples_file
        self.fused_triples_file = fused_triples_file
        self.conflicts_file = conflicts_file
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self.abstracts_by_pmid = load_abstracts_by_pmid(abstracts_file)
        self.aligned_triples, aligned_bad = load_jsonl(aligned_triples_file)
        self.fused_edges, fused_bad = load_jsonl(fused_triples_file)
        self.conflicts, conflict_bad = load_jsonl(conflicts_file)
        if aligned_bad or fused_bad or conflict_bad:
            raise ValueError("Evidence input files contain invalid JSON lines.")
        self._aligned_by_pair = self._index_aligned_triples(self.aligned_triples)
        self._fused_by_pair = self._index_fused_edges(self.fused_edges)
        self._conflicts_by_pair = self._index_conflicts(self.conflicts)

    def build_conflict_context(self, conflict, conflict_id=None):
        pair_key = entity_pair_key(conflict.get("entity_1", {}), conflict.get("entity_2", {}))
        reverse_key = entity_pair_key(conflict.get("entity_2", {}), conflict.get("entity_1", {}))
        aligned = self._aligned_by_pair.get(pair_key, []) + self._aligned_by_pair.get(reverse_key, [])
        fused = self._fused_by_pair.get(pair_key, []) + self._fused_by_pair.get(reverse_key, [])
        conflicts = self._conflicts_by_pair.get(pair_key, []) + self._conflicts_by_pair.get(reverse_key, [])
        relations = set(conflict.get("relations", []))
        if relations:
            aligned = [item for item in aligned if item.get("relation") in relations]
            fused = [item for item in fused if item.get("relation") in relations]
        aligned = self._sort_aligned(aligned)[: self.limits["max_aligned_triples"]]
        fused = self._sort_fused(fused)[: self.limits["max_fused_edges"]]
        pmids = self._select_pmids(self._pmids_from_records(aligned, fused))
        abstracts, missing = self._abstracts_for_pmids(pmids)
        return {
            "context_id": conflict_id or self._conflict_id(conflict),
            "purpose": "conflict_adjudication",
            "query": self._conflict_query(conflict),
            "entities": [conflict.get("entity_1", {}), conflict.get("entity_2", {})],
            "abstracts": abstracts,
            "aligned_triples": aligned,
            "fused_edges": fused,
            "conflicts": [conflict, *conflicts[: self.limits["max_conflicts"]]],
            "supporting_pmids": pmids,
            "missing_evidence": missing,
            "limits": dict(self.limits),
        }

    def build_question_context(self, question, top_k=8):
        candidates = self.retrieve_question_evidence(question, top_k=top_k)
        aligned = candidates["aligned_triples"][: self.limits["max_aligned_triples"]]
        fused = candidates["fused_edges"][: self.limits["max_fused_edges"]]
        conflicts = candidates["conflicts"][: self.limits["max_conflicts"]]
        pmids = self._select_pmids(self._pmids_from_records(aligned, fused))
        abstracts, missing = self._abstracts_for_pmids(pmids)
        entities = self._entities_from_records(aligned, fused)
        return {
            "context_id": self._slug_id("graph-rag", question),
            "purpose": "graph_rag_answer",
            "query": question,
            "entities": entities,
            "abstracts": abstracts,
            "aligned_triples": aligned,
            "fused_edges": fused,
            "conflicts": conflicts,
            "supporting_pmids": pmids,
            "missing_evidence": missing,
            "limits": dict(self.limits),
            "retrieval": candidates["retrieval"],
        }

    def retrieve_question_evidence(self, question, top_k=8):
        tokens = tokenize_query(question)
        aligned_scored = [
            (self._score_aligned(record, tokens), record)
            for record in self.aligned_triples
        ]
        fused_scored = [
            (self._score_fused(record, tokens), record)
            for record in self.fused_edges
        ]
        conflict_scored = [
            (self._score_conflict(record, tokens), record)
            for record in self.conflicts
        ]
        aligned = [record for score, record in sorted(aligned_scored, key=lambda item: (-item[0], _record_sort_key(item[1]))) if score > 0]
        fused = [record for score, record in sorted(fused_scored, key=lambda item: (-item[0], _record_sort_key(item[1]))) if score > 0]
        conflicts = [record for score, record in sorted(conflict_scored, key=lambda item: (-item[0], _record_sort_key(item[1]))) if score > 0]
        return {
            "aligned_triples": aligned[: max(top_k, self.limits["max_aligned_triples"])],
            "fused_edges": fused[: max(top_k, self.limits["max_fused_edges"])],
            "conflicts": conflicts[: self.limits["max_conflicts"]],
            "retrieval": {
                "mode": "lexical_entity",
                "tokens": tokens,
                "top_k": top_k,
                "aligned_candidates": sum(1 for score, _ in aligned_scored if score > 0),
                "fused_candidates": sum(1 for score, _ in fused_scored if score > 0),
                "conflict_candidates": sum(1 for score, _ in conflict_scored if score > 0),
            },
        }

    def _index_aligned_triples(self, records):
        index = defaultdict(list)
        for record in records:
            key = entity_pair_key(record.get("entity_1", {}), record.get("entity_2", {}))
            index[key].append(record)
        return index

    def _index_fused_edges(self, records):
        index = defaultdict(list)
        for record in records:
            key = entity_pair_key(record.get("entity_1", {}), record.get("entity_2", {}))
            index[key].append(record)
        return index

    def _index_conflicts(self, records):
        index = defaultdict(list)
        for record in records:
            key = entity_pair_key(record.get("entity_1", {}), record.get("entity_2", {}))
            index[key].append(record)
        return index

    def _abstracts_for_pmids(self, pmids):
        abstracts = []
        missing = []
        for pmid in pmids[: self.limits["max_abstracts"]]:
            source = self.abstracts_by_pmid.get(str(pmid))
            if not source:
                missing.append({"kind": "missing_abstract", "pmid": str(pmid)})
                continue
            abstract = source.get("abstract", "")
            if len(abstract) > self.limits["max_abstract_chars"]:
                abstract = abstract[: self.limits["max_abstract_chars"]].rstrip() + "..."
            abstracts.append({
                "pmid": str(pmid),
                "title": source.get("title", ""),
                "abstract": abstract,
                "pub_date": source.get("pub_date", ""),
            })
        if not abstracts:
            missing.append({"kind": "no_abstracts_selected", "pmids": pmids})
        return abstracts, missing

    def _pmids_from_records(self, aligned, fused):
        pmids = []
        for record in aligned:
            pmid = str(record.get("source_pmid", "")).strip()
            if pmid:
                pmids.append(pmid)
        for record in fused:
            evidence = record.get("evidence", {})
            for pmid in evidence.get("pmid_list", []):
                if pmid:
                    pmids.append(str(pmid))
        return list(dict.fromkeys(pmids))

    def _select_pmids(self, pmids):
        return pmids[: self.limits["max_supporting_pmids"]]

    def _entities_from_records(self, aligned, fused):
        seen = set()
        entities = []
        for record in [*aligned, *fused]:
            for key in ("entity_1", "entity_2"):
                entity = record.get(key, {})
                name = _clean(entity.get("name", ""))
                etype = _clean(entity.get("type", ""))
                sig = (name.lower(), etype)
                if name and sig not in seen:
                    entities.append({"name": name, "type": etype})
                    seen.add(sig)
        return entities[:24]

    def _score_aligned(self, record, tokens):
        haystack = " ".join([
            record.get("entity_1", {}).get("name", ""),
            record.get("entity_1", {}).get("type", ""),
            record.get("relation", ""),
            record.get("entity_2", {}).get("name", ""),
            record.get("entity_2", {}).get("type", ""),
            record.get("evidence_text", ""),
        ]).lower()
        return _token_score(haystack, tokens)

    def _score_fused(self, record, tokens):
        haystack = " ".join([
            record.get("entity_1", {}).get("name", ""),
            record.get("entity_1", {}).get("type", ""),
            record.get("relation", ""),
            record.get("entity_2", {}).get("name", ""),
            record.get("entity_2", {}).get("type", ""),
            record.get("review_status", ""),
        ]).lower()
        score = _token_score(haystack, tokens)
        score += float(record.get("computed_confidence", 0.0)) * 0.1
        return score

    def _score_conflict(self, record, tokens):
        haystack = " ".join([
            record.get("entity_1", {}).get("name", ""),
            record.get("entity_1", {}).get("type", ""),
            " ".join(record.get("relations", [])),
            record.get("entity_2", {}).get("name", ""),
            record.get("entity_2", {}).get("type", ""),
            record.get("reason", ""),
        ]).lower()
        return _token_score(haystack, tokens)

    def _sort_aligned(self, records):
        return sorted(
            _dedupe_records(records, self._aligned_sig),
            key=lambda item: (
                str(item.get("source_pmid", "")),
                item.get("relation", ""),
                item.get("entity_1", {}).get("name", ""),
                item.get("entity_2", {}).get("name", ""),
            ),
        )

    def _sort_fused(self, records):
        return sorted(
            _dedupe_records(records, self._fused_sig),
            key=lambda item: (
                -float(item.get("computed_confidence", 0.0)),
                item.get("relation", ""),
                item.get("entity_1", {}).get("name", ""),
                item.get("entity_2", {}).get("name", ""),
            ),
        )

    def _aligned_sig(self, record):
        return (
            record.get("source_pmid", ""),
            record.get("entity_1", {}).get("name", "").lower(),
            record.get("relation", ""),
            record.get("entity_2", {}).get("name", "").lower(),
            record.get("evidence_text", ""),
        )

    def _fused_sig(self, record):
        return (
            record.get("entity_1", {}).get("name", "").lower(),
            record.get("relation", ""),
            record.get("entity_2", {}).get("name", "").lower(),
        )

    def _conflict_id(self, conflict):
        return self._slug_id(
            "conflict",
            f"{conflict.get('entity_1', {}).get('name', '')}-{conflict.get('entity_2', {}).get('name', '')}-{'-'.join(conflict.get('relations', []))}",
        )

    def _conflict_query(self, conflict):
        e1 = conflict.get("entity_1", {}).get("name", "")
        e2 = conflict.get("entity_2", {}).get("name", "")
        rels = ", ".join(conflict.get("relations", []))
        return f"Adjudicate relation conflict between {e1} and {e2}: {rels}"

    def _slug_id(self, prefix, text):
        slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
        return f"{prefix}-{slug[:80]}" if slug else prefix


def _token_score(haystack, tokens):
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    score = 0.0
    for token, weight in counts.items():
        if token in haystack:
            score += 1.0 * weight
    return score


def _dedupe_records(records, signature_func):
    seen = set()
    deduped = []
    for record in records:
        sig = signature_func(record)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(record)
    return deduped


def _record_sort_key(record):
    return jsonish_sort_key(record)


def jsonish_sort_key(record):
    return (
        record.get("entity_1", {}).get("name", ""),
        record.get("relation", ""),
        record.get("entity_2", {}).get("name", ""),
        record.get("source_pmid", ""),
    )


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()
