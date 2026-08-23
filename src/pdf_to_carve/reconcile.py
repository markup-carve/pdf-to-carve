"""Deterministic reconciliation between trusted PDF text and visual repair output."""

from __future__ import annotations

import copy
import re
from collections import Counter
from typing import Any


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    if not isinstance(value, dict):
        return ""
    if isinstance(value.get("text"), str):
        return str(value.get("text", ""))
    fields = ("content", "children", "headers", "rows", "title", "caption", "attribution")
    return " ".join(_text(value[field]) for field in fields if field in value)


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", _text(value)).casefold()


def _tokens(value: Any) -> Counter[str]:
    return Counter(re.findall(r"[\w$]+", _text(value).casefold()))


def _provenance_by_block(document: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        entry["block"]: entry
        for entry in document.get("provenance", [])
        if isinstance(entry, dict) and isinstance(entry.get("block"), int)
    }


def _confidence_backed(index: int, provenance: dict[int, dict[str, Any]]) -> bool:
    entry = provenance.get(index, {})
    return (
        isinstance(entry.get("bbox"), list)
        and len(entry["bbox"]) == 4
        and isinstance(entry.get("confidence"), (int, float))
        and entry["confidence"] >= 0.8
    )


def _repair(
    baseline: list[dict[str, Any]], visual: dict[str, Any], visual_index: int, exact: bool
) -> dict[str, Any] | None:
    candidate = copy.deepcopy(visual)
    if len(baseline) == 1 and baseline[0]["type"] == candidate.get("type") == "code_block":
        if _compact(baseline[0]) != _compact(candidate):
            return None
        if baseline[0].get("language"):
            candidate["language"] = baseline[0]["language"]
        return candidate
    if not exact:
        return candidate if candidate.get("type") in {"code_block", "figure"} else None
    if len(baseline) == 1 and baseline[0]["type"] == candidate.get("type"):
        if candidate["type"] == "table" and baseline[0].get("alignments"):
            candidate.setdefault("alignments", baseline[0]["alignments"])
            return candidate
        if candidate["type"] == "figure":
            candidate["src"] = baseline[0]["src"]
            return candidate
        return baseline[0]
    if candidate.get("type") in {"table", "list", "quote", "figure", "code_block"}:
        return candidate
    return None


def reconcile_hybrid(
    baseline: dict[str, Any], visual: dict[str, Any], *, max_baseline_span: int = 12
) -> dict[str, Any]:
    """Apply evidence-preserving visual repairs to deterministic text extraction."""
    base_blocks = baseline.get("blocks", [])
    visual_blocks = visual.get("blocks", [])
    provenance = _provenance_by_block(visual)
    mappings: list[tuple[int, int, dict[str, Any]]] = []
    cursor = 0
    for visual_index, candidate in enumerate(visual_blocks):
        candidate_compact = _compact(candidate)
        candidate_tokens = _tokens(candidate)
        if not candidate_compact and candidate.get("type") != "figure":
            continue
        match = None
        for start in range(cursor, len(base_blocks)):
            for end in range(start + 1, min(len(base_blocks), start + max_baseline_span) + 1):
                group = base_blocks[start:end]
                exact = _compact(group) == candidate_compact
                covered = bool(candidate_tokens) and _tokens(group) <= candidate_tokens
                if exact or (
                    covered
                    and candidate.get("type") in {"code_block", "figure"}
                    and _confidence_backed(visual_index, provenance)
                ):
                    repair = _repair(group, candidate, visual_index, exact)
                    if repair is not None:
                        match = (start, end, repair)
                        break
            if match:
                break
        if match:
            mappings.append(match)
            cursor = match[1]

    blocks = []
    cursor = 0
    for start, end, repair in mappings:
        blocks.extend(copy.deepcopy(base_blocks[cursor:start]))
        blocks.append(repair)
        cursor = end
    blocks.extend(copy.deepcopy(base_blocks[cursor:]))
    result = {key: copy.deepcopy(value) for key, value in baseline.items() if key != "blocks"}
    result["version"] = 1
    result["blocks"] = blocks
    return result
