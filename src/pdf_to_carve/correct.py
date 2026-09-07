"""Local, validated interactive correction of extraction JSON."""

from __future__ import annotations

import json
from typing import TextIO

from .model import (
    HUMAN_CORRECTED_WARNING,
    Document,
    DocumentError,
    Provenance,
    document_to_json,
)


def needs_review(entry: Provenance, threshold: float) -> bool:
    """Return whether provenance should enter the correction queue."""
    return HUMAN_CORRECTED_WARNING not in entry.warnings and (
        entry.confidence is None or entry.confidence < threshold or bool(entry.warnings)
    )


def correct_interactively(
    document: Document,
    *,
    input_stream: TextIO,
    output_stream: TextIO,
    threshold: float = 0.85,
) -> Document:
    """Review uncertain blocks, validating replacements before accepting them.

    Enter keeps a block unchanged and a compact JSON object replaces it. Invalid
    replacements are rejected without modifying the document and the same block
    is prompted again. Provider confidence is never rewritten by human review.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("confidence threshold must be between 0 and 1")
    raw = document_to_json(document)
    queued = [entry for entry in document.provenance if needs_review(entry, threshold)]
    print(f"pdf-to-carve: {len(queued)} block(s) need review", file=output_stream)
    for queued_entry in queued:
        index = queued_entry.block
        while True:
            confidence = (
                "unknown" if queued_entry.confidence is None else f"{queued_entry.confidence:.3f}"
            )
            print(
                f"\nblock {index} page {queued_entry.page} confidence {confidence}",
                file=output_stream,
            )
            for warning in queued_entry.warnings:
                print(f"warning: {warning}", file=output_stream)
            print(json.dumps(raw["blocks"][index], ensure_ascii=False), file=output_stream)
            print("replacement JSON or Enter to keep: ", end="", file=output_stream)
            output_stream.flush()
            answer = input_stream.readline()
            if answer == "":
                print("input closed; remaining blocks were not reviewed", file=output_stream)
                return Document.from_json(raw)
            if not answer.strip():
                break
            try:
                replacement = json.loads(answer)
                candidate = {**raw, "blocks": list(raw["blocks"])}
                candidate["blocks"][index] = replacement
                candidate["provenance"] = [
                    {
                        **item,
                        **(
                            {
                                "warnings": [
                                    *item.get("warnings", []),
                                    HUMAN_CORRECTED_WARNING,
                                ]
                            }
                            if item["block"] == index
                            and HUMAN_CORRECTED_WARNING not in item.get("warnings", [])
                            else {}
                        ),
                    }
                    for item in raw.get("provenance", [])
                ]
                validated = Document.from_json(candidate)
            except (json.JSONDecodeError, DocumentError) as exc:
                print(f"invalid replacement: {exc}", file=output_stream)
                continue
            raw = document_to_json(validated)
            break
    return Document.from_json(raw)
