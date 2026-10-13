
"""Local policy retrieval with query-aware document selection."""

import re
from pathlib import Path

KNOWLEDGE_BASE_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "knowledge_base"
)

STOP_WORDS = {
    "a", "an", "the", "is", "are", "am", "was", "were",
    "be", "been", "being", "to", "of", "in", "on", "at",
    "for", "and", "or", "but", "if", "it", "this", "that",
    "i", "me", "my", "we", "our", "you", "your", "can",
    "could", "would", "should", "do", "does", "did",
    "what", "when", "where", "how", "please", "tell",
    "work", "works", "working",
}

WORD_NORMALIZATION = {
    "return": "refund",
    "returns": "refund",
    "returning": "refund",
    "refunds": "refund",
    "refunded": "refund",
    "refundable": "refund",
    "reimburse": "refund",
    "reimbursement": "refund",
    "reimbursements": "refund",
    "reimbursed": "refund",
}

REFUND_TERMS = {
    "refund", "money", "back", "reimburse", "reimbursement",
}

DELIVERY_TERMS = {
    "delivery", "delayed", "late", "tracking", "arrived",
    "package", "parcel", "shipment", "shipping", "order",
}

POLICY_HINTS = {
    "refund_policy.txt": REFUND_TERMS,
    "delivery_policy.txt": DELIVERY_TERMS,
}


def _tokenize(text: str) -> set[str]:
    """Normalize text into useful lowercase search terms."""
    words = re.findall(r"\b[a-z0-9_]+\b", text.lower())

    return {
        WORD_NORMALIZATION.get(word, word)
        for word in words
        if word not in STOP_WORDS
    }


def search_knowledge_base(
    query: str,
    top_k: int = 2,
) -> list[dict]:
    """Retrieve relevant policies and prioritize clear policy topics."""
    if not query or not query.strip() or top_k < 1:
        return []

    if not KNOWLEDGE_BASE_DIR.exists():
        return []

    query_terms = _tokenize(query)
    if not query_terms:
        return []

    refund_requested = bool(query_terms & REFUND_TERMS)
    delivery_requested = bool(query_terms & DELIVERY_TERMS)

    files = sorted(KNOWLEDGE_BASE_DIR.glob("*.txt"))
    files += sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))

    results = []

    for file_path in files:
        # When the question clearly targets one policy, skip unrelated files.
        if refund_requested and not delivery_requested:
            if file_path.name == "delivery_policy.txt":
                continue

        if delivery_requested and not refund_requested:
            if file_path.name == "refund_policy.txt":
                continue

        content = file_path.read_text(encoding="utf-8")
        document_terms = _tokenize(content)
        matching_terms = query_terms & document_terms

        if not matching_terms:
            continue

        score = len(matching_terms) / len(query_terms)

        policy_hints = {
            WORD_NORMALIZATION.get(word, word)
            for word in POLICY_HINTS.get(file_path.name, set())
        }
        hint_matches = query_terms & policy_hints

        if hint_matches:
            score += 0.5 * len(hint_matches) / len(query_terms)

        results.append({
            "source": file_path.name,
            "content": content.strip(),
            "score": round(score, 4),
            "matched_terms": sorted(matching_terms),
        })

    results.sort(key=lambda item: (-item["score"], item["source"]))

    return results[:top_k]
