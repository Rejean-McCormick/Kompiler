from __future__ import annotations

import re
from collections import defaultdict, deque

from kompiler.protocol.canonical import canonical_bytes
from kompiler.protocol.models import NormalizedRecord, QueryBudget

# Lexical relevance is a retrieval heuristic, never a trust, authority or truth score.
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def _terms(value: str) -> set[str]:
    return {word for word in _WORD.findall(value.casefold()) if len(word) > 1}


def _lexical_score(record: NormalizedRecord, query_terms: set[str]) -> int:
    if not query_terms:
        return 0
    # Scope relevance to actual record content, not adapter/source metadata.
    payload = record.model_dump(mode="json", exclude_none=True)
    content = {key: payload.get(key) for key in ("semantic_id", "statement", "content")}
    serialized = canonical_bytes(content).decode("utf-8")
    return len(_terms(serialized) & query_terms)


def select_records(
    records: list[NormalizedRecord], budget: QueryBudget, *, topic: str = ""
) -> tuple[list[NormalizedRecord], bool]:
    """Deterministic per-target fair selection with optional lexical ordering.

    The default 'balanced' mode retains existing order/behavior. In 'lexical'
    mode only the *order within each target* changes: every target still gets
    turns, and zero-overlap records are still eligible. No record is treated
    as authoritative because of its ranking.
    """
    max_items = budget.max_items or len(records)
    max_bytes = budget.max_bytes or 2**63 - 1
    if budget.target_tokens:
        max_bytes = min(max_bytes, budget.target_tokens * 4)
    # Retain the incoming canonical order when all records fit. This is
    # backwards-compatible and avoids unnecessary ranking/serialization work.
    encoded_sizes = [len(canonical_bytes(record.model_dump(mode="json", exclude_none=True)))
                     for record in records]
    total_size = 2 + sum(encoded_sizes) + max(0, len(records) - 1)
    if len(records) <= max_items and total_size <= max_bytes:
        return records, False

    groups: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in records:
        groups[record.target_id or ""].append(record)
    if budget.selection_mode == "lexical":
        terms = _terms(topic)
        if terms:
            for group in groups.values():
                # Stable sorting preserves canonical record order for equal scores.
                group.sort(key=lambda record: -_lexical_score(record, terms))

    candidates = {target: deque(group) for target, group in groups.items()}
    selected: list[NormalizedRecord] = []
    size = 2  # Size of the empty JSON array, excluding record delimiters.
    targets = sorted(candidates)
    while len(selected) < max_items:
        progressed = False
        for target in targets:
            if not candidates[target]:
                continue
            candidate = candidates[target].popleft()
            encoded = canonical_bytes(candidate.model_dump(mode="json", exclude_none=True))
            increment = len(encoded) + (1 if selected else 0)
            if size + increment > max_bytes:
                continue
            selected.append(candidate)
            size += increment
            progressed = True
            if len(selected) >= max_items:
                break
        if not progressed and not any(candidates.values()):
            break
    return selected, len(selected) < len(records)
