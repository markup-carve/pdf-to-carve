"""Permissively licensed PDFium backend for extraction and rendering."""

from __future__ import annotations

import hashlib
import statistics
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium


def _range(document: pdfium.PdfDocument, start: int, end: int | None) -> range:
    last = len(document) if end is None else min(end, len(document))
    if start < 1 or start > last:
        raise ValueError(f"invalid page range {start}-{last} for {len(document)} pages")
    return range(start - 1, last)


def _objects(page: pdfium.PdfPage) -> list[dict[str, Any]]:
    """Return text objects in visual column-major order and top-left coordinates."""
    height = page.get_height()
    text_page = page.get_textpage()
    try:
        fragments = []
        for item in page.get_objects(
            filter=(pdfium.raw.FPDF_PAGEOBJ_TEXT,), max_depth=8, textpage=text_page
        ):
            text = item.extract().replace("\r", " ").replace("\n", " ")
            if not text.strip():
                continue
            left, bottom, right, top = item.get_bounds()
            fragments.append(
                {
                    "text": text,
                    "size": float(item.get_font_size()),
                    "bbox": [left, height - top, right, height - bottom],
                }
            )
        rows: list[dict[str, Any]] = []
        for item in fragments:
            if not rows:
                rows.append(item)
                continue
            previous = rows[-1]
            old = previous["bbox"]
            new = item["bbox"]
            same_line = (
                abs((old[1] + old[3]) / 2 - (new[1] + new[3]) / 2)
                <= max(previous["size"], item["size"]) * 0.45
            )
            forward = (
                new[0] >= old[0] and new[0] - old[2] < max(previous["size"], item["size"]) * 1.5
            )
            if not same_line or not forward:
                item["text"] = item["text"].strip()
                rows.append(item)
                continue
            gap = max(0.0, new[0] - old[2])
            separator = ""
            if (
                not previous["text"].endswith((" ", "\t"))
                and not item["text"].startswith((" ", "\t"))
                and gap > max(previous["size"], item["size"]) * 0.25
            ):
                separator = " "
            previous["text"] = previous["text"] + separator + item["text"]
            previous["size"] = max(previous["size"], item["size"])
            previous["bbox"] = [
                min(old[0], new[0]),
                min(old[1], new[1]),
                max(old[2], new[2]),
                max(old[3], new[3]),
            ]
        for row in rows:
            row["text"] = row["text"].strip()
        return rows
    finally:
        text_page.close()


def extract_text_pdf(path: Path, start: int = 1, end: int | None = None) -> dict[str, Any]:
    document = pdfium.PdfDocument(path)
    try:
        pages = list(_range(document, start, end))
        objects = [_objects(document[number]) for number in pages]
        sizes = [item["size"] for page in objects for item in page]
        body_size = statistics.median(sizes) if sizes else 11.0
        blocks = []
        for page_index, page in enumerate(objects):
            if page_index:
                blocks.append({"type": "page_break"})
            for item in page:
                value, size = item["text"], item["size"]
                if size >= body_size * 1.6 and len(value) <= 160:
                    level = 1
                elif size >= body_size * 1.3 and len(value) <= 180:
                    level = 2
                elif size >= body_size * 1.12 and len(value) <= 200:
                    level = 3
                else:
                    level = 0
                kind: dict[str, Any] = {
                    "type": "heading" if level else "paragraph",
                    "content": [{"type": "text", "text": value}],
                }
                if level:
                    kind["level"] = level
                blocks.append(kind)
        metadata = document.get_metadata_dict()
        result: dict[str, Any] = {"version": 1, "blocks": blocks}
        if metadata.get("Title", "").strip():
            result["title"] = metadata["Title"].strip()
        if metadata.get("Author", "").strip():
            result["author"] = metadata["Author"].strip()
        return result
    finally:
        document.close()


def text_coverage(path: Path, start: int = 1, end: int | None = None) -> float:
    document = pdfium.PdfDocument(path)
    try:
        counts = []
        for number in _range(document, start, end):
            text_page = document[number].get_textpage()
            try:
                counts.append(len("".join(text_page.get_text_range().split())))
            finally:
                text_page.close()
        return sum(counts) / len(counts) if counts else 0.0
    finally:
        document.close()


def positioned_text(path: Path, start: int = 1, end: int | None = None) -> list[dict[str, Any]]:
    document = pdfium.PdfDocument(path)
    try:
        result = []
        for number in _range(document, start, end):
            page = document[number]
            width, height = page.get_size()
            for item in _objects(page):
                result.append(
                    {
                        "page": number + 1,
                        "bbox": [round(float(value), 2) for value in item["bbox"]],
                        "page_size": [round(width, 2), round(height, 2)],
                        "text": item["text"],
                    }
                )
        return result
    finally:
        document.close()


def render_pages(
    path: Path, directory: Path, start: int, end: int | None, *, dpi: int, max_pages: int
) -> list[Path]:
    document = pdfium.PdfDocument(path)
    try:
        pages = list(_range(document, start, end))
        if len(pages) > max_pages:
            raise ValueError(f"selected range has {len(pages)} pages; maximum is {max_pages}")
        result = []
        for number in pages:
            target = directory / f"page-{number + 1}.png"
            bitmap = document[number].render(scale=dpi / 72, rev_byteorder=True)
            try:
                bitmap.to_pil().save(target)
            finally:
                bitmap.close()
            result.append(target)
        return result
    finally:
        document.close()


def extract_embedded_images(path: Path, output_dir: Path) -> list[Path]:
    """Extract unique raster page objects through PDFium's decoded bitmap API."""
    output_dir.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(path)
    seen: set[str] = set()
    result = []
    try:
        for page_number, page in enumerate(document):
            figure_number = 0
            for item in page.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,), max_depth=8):
                bitmap = item.get_bitmap(render=True, scale_to_original=True)
                try:
                    image = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
                blob = image.tobytes()
                digest = hashlib.sha256(blob).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                figure_number += 1
                target = output_dir / f"page-{page_number + 1}-figure-{figure_number}.png"
                image.save(target)
                result.append(target)
        return result
    finally:
        document.close()
