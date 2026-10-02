"""Source traceability and conservative evidence triage, never entailment.

All offsets refer to the unchanged title/abstract snapshot. Fuzzy matches are
suggestions only. Entity coverage is lexical and cannot verify a relationship.
"""

import re
import unicodedata
from difflib import SequenceMatcher

VERSION = "traceability_v1"
CONFIG = {"minimum_tokens": 6, "fuzzy_suggestion_threshold": 0.80,
          "automatic_fuzzy_acceptance": False}
PUNCTUATION = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"',
                           "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2212": "-"})
FLAGS = {
    "negation_requires_review": r"\b(?:not|no|neither|without|failed|lack)\b",
    "uncertainty_requires_review": r"\b(?:may|might|could|potential|hypothes\w*|suggest\w*)\b",
    "experimental_context_requires_review": r"\b(?:mice|mouse|murine|in vitro|cell lines?|animal model)\b",
}
PREDICATE = re.compile(
    r"\b(?:is|are|was|were|has|have|had|caus\w*|associat\w*|correlat\w*|"
    r"improv\w*|reduc\w*|increas\w*|decreas\w*|regulat\w*|express\w*|"
    r"treat\w*|affect\w*|target\w*|result\w*|lead\w*|leads|linked|"
    r"interaction\w*|interact\w*|deficien\w*|delet\w*|mutat\w*|"
    r"elevat\w*|inhibit\w*|activat\w*|protect\w*|prevent\w*|"
    r"benefit\w*|observ\w*|demonstrat\w*|found|show\w*|underl\w*|"
    r"encod\w*|involv\w*|loss|suppress\w*)\b", re.I)


def normalize_with_offsets(value):
    """Normalize typography/spacing while retaining original character ranges."""
    chars, offsets = [], []
    for index, char in enumerate(str(value or "")):
        normalized = unicodedata.normalize("NFKC", char).translate(PUNCTUATION).casefold()
        for item in normalized:
            if item.isspace():
                if chars and chars[-1] == " ":
                    offsets[-1] = (offsets[-1][0], index + 1)
                    continue
                item = " "
            chars.append(item)
            offsets.append((index, index + 1))
    return "".join(chars), offsets


def normalized_text(value):
    return normalize_with_offsets(value)[0].strip()


def source_sentences(text):
    # Boundaries require whitespace (or a newline); decimal points, gene variant
    # notation and punctuation inside a token must never truncate source context.
    # This remains a conservative heuristic, not a biomedical sentence parser.
    start = 0
    for boundary in re.finditer(r'(?<=[.!?])(?:["\x27)\]]*)\s+(?=[A-Z])|\n+', text):
        end = boundary.start()
        while end < boundary.end() and not text[end].isspace():
            end += 1
        if text[start:end].strip():
            yield start, end, text[start:end]
        start = boundary.end()
    if text[start:].strip():
        yield start, len(text), text[start:]


def locate_span(span, source, suggest_fuzzy=True):
    texts = {key: str(source.get(key, "")) for key in ("title", "abstract")}
    if not span or not str(span).strip():
        return {"status": "missing_evidence", "segments": [], "suggestion": None}
    span = str(span).strip()
    for key, text in texts.items():
        start = text.find(span)
        if start >= 0:
            return {"status": "exact", "segments": [{"field": key, "start": start,
                    "end": start + len(span), "text": text[start:start + len(span)]}], "suggestion": None}
    normalized = normalized_text(span)
    for key, text in texts.items():
        haystack, offsets = normalize_with_offsets(text)
        start = haystack.find(normalized)
        if normalized and start >= 0:
            a, b = offsets[start][0], offsets[start + len(normalized) - 1][1]
            return {"status": "normalized", "segments": [{"field": key, "start": a,
                    "end": b, "text": text[a:b]}], "suggestion": None}
    # Ellipsis fragments must occur in order within ONE source field. Never
    # concatenate title and abstract or silently substitute a guessed sentence.
    fragments = [normalized_text(x) for x in re.split(r"\.{3,}|\u2026", span)]
    if len(fragments) > 1 and all(len(x) >= 5 and re.search(r"\w", x) for x in fragments):
        for key, text in texts.items():
            haystack, offsets = normalize_with_offsets(text)
            cursor, segments = 0, []
            for fragment in fragments:
                start = haystack.find(fragment, cursor)
                if start < 0:
                    break
                a, b = offsets[start][0], offsets[start + len(fragment) - 1][1]
                segments.append({"field": key, "start": a, "end": b, "text": text[a:b]})
                cursor = start + len(fragment)
            if len(segments) == len(fragments):
                return {"status": "ordered_fragments", "segments": segments, "suggestion": None}
    suggestion = None
    if suggest_fuzzy and len(normalized.split()) >= 4:
        for key, text in texts.items():
            for start, end, sentence in source_sentences(text):
                score = SequenceMatcher(None, normalized, normalized_text(sentence), autojunk=False).ratio()
                if score >= CONFIG["fuzzy_suggestion_threshold"] and (suggestion is None or score > suggestion["similarity"]):
                    suggestion = {"field": key, "start": start, "end": end,
                                  "text": sentence, "similarity": round(score, 4)}
    return {"status": "not_located", "segments": [], "suggestion": suggestion}


def endpoint_forms(entity, source, dictionary):
    name, etype = str(entity.get("name", "")), str(entity.get("type", "")).lower()
    forms = {normalized_text(name)}
    mapping = dictionary.get(etype, {})
    canonical = normalized_text(mapping.get(name.lower(), name))
    forms.add(canonical)
    forms.update(normalized_text(alias) for alias, target in mapping.items()
                 if normalized_text(target) == canonical)
    # Only use acronym definitions present in this source, not embedding aliases.
    text = str(source.get("title", "")) + " " + str(source.get("abstract", ""))
    for match in re.finditer(r"([A-Za-z][A-Za-z -]{3,100})\s*\(([A-Za-z][A-Za-z0-9-]{1,15})\)", text):
        long_name, short_name = normalized_text(match.group(1)), normalized_text(match.group(2))
        if short_name in forms or any(long_name.endswith(f) for f in forms if f):
            forms.add(short_name)
    return sorted(f for f in forms if f)


def contains_form(text, forms):
    text = normalized_text(text)
    return any(re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", text) for form in forms)


def validate_evidence(record, source, dictionary=None, suggest_fuzzy=True):
    if source is None:
        return {"version": VERSION, "location_status": "missing_source", "segments": [],
                "suggestion": None, "endpoint_coverage": [False, False],
                "flags": ["missing_source"], "traceable": False, "eligible_span": False,
                "triage": "needs_review", "semantic_support": "not_evaluated"}
    dictionary = dictionary or {}
    span = str(record.get("evidence_text", ""))
    located = locate_span(span, source, suggest_fuzzy=suggest_fuzzy)
    traceable = bool(located["segments"])
    flags = []
    if not traceable:
        flags.append(located["status"])
    if located["status"] == "ordered_fragments":
        flags.append("ellipsis_context_requires_review")
    coverage = [contains_form(span, endpoint_forms(record.get(key, {}), source, dictionary))
                for key in ("entity_1", "entity_2")]
    if not all(coverage):
        flags.append("missing_endpoint_in_span")
    if len(re.findall(r"\b\w+\b", span)) < CONFIG["minimum_tokens"]:
        flags.append("short_fragment")
    if not PREDICATE.search(span):
        flags.append("no_predicate_cue")
    # Inspect the containing source sentence too: a short positive fragment
    # must not escape review when its surrounding statement contains negation.
    contexts = [span]
    for segment in located["segments"]:
        text = str(source.get(segment["field"], ""))
        contexts.extend(sentence for a, b, sentence in source_sentences(text)
                        if a <= segment["start"] < b)
    for flag, pattern in FLAGS.items():
        if any(re.search(pattern, context, re.I) for context in contexts):
            flags.append(flag)
    eligible = traceable and not flags
    return {"version": VERSION, "location_status": located["status"],
            "segments": located["segments"], "suggestion": located["suggestion"],
            "endpoint_coverage": coverage, "flags": flags, "traceable": traceable,
            "eligible_span": eligible,
            "triage": "traceable_candidate" if eligible else "needs_review",
            "semantic_support": "not_evaluated"}
