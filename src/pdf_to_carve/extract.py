"""Deterministic extraction for PDFs that already contain usable text."""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any


def _pymupdf() -> Any:
    try:
        import pymupdf
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "the PyMuPDF backend requires the optional 'pdf-to-carve[pymupdf]' extra"
        ) from exc
    return pymupdf


def _text(value: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": value.strip()}]


def extract_text_pdf(path: Path, start: int = 1, end: int | None = None) -> dict[str, Any]:
    """Extract a conservative document model from positioned PDF text."""
    pymupdf = _pymupdf()
    doc = pymupdf.open(path)
    try:
        if not doc.page_count:
            return {"version": 1, "blocks": []}
        last = doc.page_count if end is None else min(end, doc.page_count)
        if start < 1 or start > last:
            raise ValueError(f"invalid page range {start}-{last} for {doc.page_count} pages")
        pages = list(range(start - 1, last))
        sizes = []
        page_dicts = []
        for number in pages:
            page_data = doc[number].get_text("dict", sort=True)
            page_dicts.append(page_data)
            for block in page_data["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            sizes.append(float(span["size"]))
        body_size = statistics.median(sizes) if sizes else 11.0
        blocks = []
        for page_index, page_data in enumerate(page_dicts):
            if page_index:
                blocks.append({"type": "page_break"})
            for raw in page_data["blocks"]:
                if "lines" not in raw:
                    continue
                lines = []
                block_sizes = []
                for line in raw["lines"]:
                    value = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                    if value:
                        lines.append(value)
                        block_sizes.extend(
                            float(span["size"])
                            for span in line.get("spans", [])
                            if span.get("text", "").strip()
                        )
                value = " ".join(lines).strip()
                if not value:
                    continue
                size = max(block_sizes, default=body_size)
                if size >= body_size * 1.6 and len(value) <= 160:
                    level = 1
                elif size >= body_size * 1.3 and len(value) <= 180:
                    level = 2
                elif size >= body_size * 1.12 and len(value) <= 200:
                    level = 3
                else:
                    level = 0
                if level:
                    blocks.append({"type": "heading", "level": level, "content": _text(value)})
                else:
                    blocks.append({"type": "paragraph", "content": _text(value)})
        metadata = doc.metadata or {}
        result: dict[str, Any] = {"version": 1, "blocks": blocks}
        if metadata.get("title", "").strip():
            result["title"] = metadata["title"].strip()
        if metadata.get("author", "").strip():
            result["author"] = metadata["author"].strip()
        return result
    finally:
        doc.close()


def text_coverage(path: Path, start: int = 1, end: int | None = None) -> float:
    """Return average extracted non-whitespace characters per selected page."""
    pymupdf = _pymupdf()
    doc = pymupdf.open(path)
    try:
        last = doc.page_count if end is None else min(end, doc.page_count)
        pages = range(start - 1, last)
        counts = [len("".join(doc[n].get_text().split())) for n in pages]
        return sum(counts) / len(counts) if counts else 0.0
    finally:
        doc.close()
