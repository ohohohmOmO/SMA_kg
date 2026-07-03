import re
from collections import Counter
from difflib import SequenceMatcher


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
DEFAULT_MIN_FUZZY_SCORE = 0.9
MIN_FUZZY_TOKENS = 4
MIN_FUZZY_CHARS = 20


def align_evidence_span(evidence_text, abstract_text, min_fuzzy_score=DEFAULT_MIN_FUZZY_SCORE):
    evidence = str(evidence_text or "").strip()
    abstract = str(abstract_text or "")
    if not evidence or not abstract:
        return _alignment(False, "none", 0.0)

    exact_start = abstract.lower().find(evidence.lower())
    if exact_start >= 0:
        return _alignment(
            True,
            "exact",
            1.0,
            exact_start,
            exact_start + len(evidence),
            abstract,
        )

    normalized_evidence, _ = _normalize_with_offsets(evidence)
    normalized_abstract, abstract_offsets = _normalize_with_offsets(abstract)
    if normalized_evidence:
        normalized_start = normalized_abstract.find(normalized_evidence)
        if normalized_start >= 0:
            start = abstract_offsets[normalized_start]
            end = abstract_offsets[normalized_start + len(normalized_evidence) - 1] + 1
            return _alignment(True, "normalized", 1.0, start, end, abstract)

    evidence_tokens = list(TOKEN_PATTERN.finditer(evidence))
    abstract_tokens = list(TOKEN_PATTERN.finditer(abstract))
    if (
        len(evidence_tokens) < MIN_FUZZY_TOKENS
        or len(normalized_evidence) < MIN_FUZZY_CHARS
        or not abstract_tokens
    ):
        return _alignment(False, "none", 0.0)

    target = _normalize_for_similarity(evidence)
    evidence_token_counts = Counter(_normalize_token(match.group()) for match in evidence_tokens)
    best = (0.0, -1, -1)
    best_coverage = (0.0, -1, -1)
    target_token_count = len(evidence_tokens)
    min_window = max(1, target_token_count - 2)
    max_window = min(len(abstract_tokens), target_token_count + 2)
    for window_size in range(min_window, max_window + 1):
        for token_start in range(0, len(abstract_tokens) - window_size + 1):
            token_end = token_start + window_size - 1
            start = abstract_tokens[token_start].start()
            end = abstract_tokens[token_end].end()
            candidate_token_counts = Counter(
                _normalize_token(match.group())
                for match in abstract_tokens[token_start:token_end + 1]
            )
            overlap = sum(
                min(count, candidate_token_counts.get(token, 0))
                for token, count in evidence_token_counts.items()
            )
            coverage = overlap / sum(evidence_token_counts.values())
            if (
                coverage > best_coverage[0]
                or (coverage == best_coverage[0] and (best_coverage[1] < 0 or start < best_coverage[1]))
            ):
                best_coverage = (coverage, start, end)
            if any(
                candidate_token_counts.get(token, 0) < count
                for token, count in evidence_token_counts.items()
            ):
                continue
            candidate = _normalize_for_similarity(abstract[start:end])
            score = SequenceMatcher(None, target, candidate, autojunk=False).ratio()
            if score > best[0] or (score == best[0] and (best[1] < 0 or start < best[1])):
                best = (score, start, end)

    threshold = max(0.0, min(1.0, float(min_fuzzy_score)))
    if best[1] >= 0:
        score, start, end = best
        if score >= threshold:
            return _alignment(True, "fuzzy", score, start, end, abstract)
        return _alignment(False, "none", score, start, end, abstract)
    coverage, start, end = best_coverage
    return _alignment(False, "none", coverage, start, end, abstract)


def _normalize_with_offsets(text):
    normalized = []
    offsets = []
    for index, char in enumerate(str(text or "")):
        if char.isalnum():
            normalized.append(char.lower())
            offsets.append(index)
    return "".join(normalized), offsets


def _normalize_for_similarity(text):
    tokens = TOKEN_PATTERN.findall(str(text or "").lower())
    return " ".join(re.sub(r"[^a-z0-9]+", "", token) for token in tokens)


def _normalize_token(token):
    return re.sub(r"[^a-z0-9]+", "", str(token or "").lower())


def _alignment(valid, method, score, start=-1, end=-1, abstract=""):
    matched_text = abstract[start:end] if start >= 0 and end >= start else ""
    return {
        "valid": bool(valid),
        "method": method,
        "score": round(float(score), 3),
        "start_char": int(start),
        "end_char": int(end),
        "matched_text": matched_text,
    }
