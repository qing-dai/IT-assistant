from config import KEEP_TERMS
from preprocess import normalize_text


def matches_keep_rule(text: str) -> bool:
    normalized = normalize_text(text)
    return any(term in normalized for term in KEEP_TERMS)


def matches_keep_rule_in_title(title: str) -> bool:
    normalized = normalize_text(title)
    return any(term in normalized for term in KEEP_TERMS)
