"""Permissively licensed PDFium backend for extraction and rendering."""

from __future__ import annotations

import ctypes
import hashlib
import re
import statistics
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium


def _page_links(page: pdfium.PdfPage) -> list[dict[str, Any]]:
    """Return external URI annotations in top-left page coordinates."""
    height = page.get_height()
    result = []
    count = pdfium.raw.FPDFPage_GetAnnotCount(page.raw)
    for index in range(count):
        annotation = pdfium.raw.FPDFPage_GetAnnot(page.raw, index)
        if not annotation:
            continue
        try:
            if pdfium.raw.FPDFAnnot_GetSubtype(annotation) != pdfium.raw.FPDF_ANNOT_LINK:
                continue
            link = pdfium.raw.FPDFAnnot_GetLink(annotation)
            action = pdfium.raw.FPDFLink_GetAction(link) if link else None
            if not action or pdfium.raw.FPDFAction_GetType(action) != pdfium.raw.PDFACTION_URI:
                continue
            length = pdfium.raw.FPDFAction_GetURIPath(page.pdf.raw, action, None, 0)
            if length <= 1 or length > 65_536:
                continue
            buffer = ctypes.create_string_buffer(length)
            if not pdfium.raw.FPDFAction_GetURIPath(page.pdf.raw, action, buffer, length):
                continue
            rectangle = pdfium.raw.FS_RECTF()
            if not pdfium.raw.FPDFAnnot_GetRect(annotation, ctypes.byref(rectangle)):
                continue
            result.append(
                {
                    "bbox": [
                        float(rectangle.left),
                        height - float(rectangle.top),
                        float(rectangle.right),
                        height - float(rectangle.bottom),
                    ],
                    "url": buffer.value.decode("utf-8", errors="replace"),
                }
            )
        finally:
            pdfium.raw.FPDFPage_CloseAnnot(annotation)
    return result


def _page_paths(page: pdfium.PdfPage) -> list[list[float]]:
    """Return path bounds in top-left page coordinates for decoration matching."""
    height = page.get_height()
    return [
        [left, height - top, right, height - bottom]
        for item in page.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_PATH,), max_depth=8)
        for left, bottom, right, top in [item.get_bounds()]
    ]


def _horizontal_coverage(first: list[float], second: list[float]) -> float:
    overlap = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    return overlap / max(0.01, first[2] - first[0])


def _vertical_coverage(first: list[float], second: list[float]) -> float:
    overlap = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    return overlap / max(0.01, first[3] - first[1])


def _decorate_fragment(
    fragment: dict[str, Any], links: list[dict[str, Any]], paths: list[list[float]]
) -> None:
    bbox = fragment["bbox"]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    for link in links:
        if (
            _horizontal_coverage(bbox, link["bbox"]) >= 0.7
            and _vertical_coverage(bbox, link["bbox"]) >= 0.5
        ):
            fragment["url"] = link["url"]
            break
    for path in paths:
        path_width = path[2] - path[0]
        path_height = path[3] - path[1]
        if path_width > width + fragment["size"] * 1.5:
            continue
        horizontal = _horizontal_coverage(bbox, path)
        if horizontal < 0.7:
            continue
        if (
            path_height <= max(1.5, fragment["size"] * 0.2)
            and bbox[3] - fragment["size"] * 0.15 <= path[1] <= bbox[3] + fragment["size"] * 0.45
        ):
            fragment["underline"] = True
        elif height * 0.65 <= path_height <= height * 1.8 and _vertical_coverage(bbox, path) >= 0.6:
            fragment["highlight"] = True


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
        links = _page_links(page)
        paths = _page_paths(page)
        fragments = []
        for item in page.get_objects(
            filter=(pdfium.raw.FPDF_PAGEOBJ_TEXT,), max_depth=8, textpage=text_page
        ):
            text = item.extract().replace("\r", " ").replace("\n", " ")
            if not text.strip():
                continue
            left, bottom, right, top = item.get_bounds()
            font = item.get_font()
            base_font = font.get_base_name().lower()
            family = font.get_family_name().lower()
            fragment = {
                "text": text,
                "size": float(item.get_font_size()),
                "bbox": [left, height - top, right, height - bottom],
                "bold": any(name in base_font for name in ("bold", "heavy", "black")),
                "italic": any(name in base_font for name in ("italic", "oblique", "slanted")),
                "monospace": any(
                    name in base_font or name in family for name in ("mono", "courier")
                ),
            }
            _decorate_fragment(fragment, links, paths)
            fragments.append(fragment)
        rows: list[dict[str, Any]] = []
        for item in fragments:
            if not rows:
                item["runs"] = [dict(item)]
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
                item["runs"] = [dict(item)]
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
            if (
                not separator
                and previous["text"].endswith((".", "?", "!", ":", ";"))
                and item["text"][:1].isupper()
            ):
                separator = " "
            if item["text"][:1] in ",.;:!?)]}" and previous["text"].endswith((" ", "\t")):
                previous["text"] = previous["text"].rstrip()
                previous["runs"][-1]["text"] = previous["runs"][-1]["text"].rstrip()
            previous["text"] = previous["text"] + separator + item["text"]
            run = dict(item)
            run["text"] = separator + run["text"]
            previous["runs"].append(run)
            previous["size"] = max(previous["size"], item["size"])
            previous["bbox"] = [
                min(old[0], new[0]),
                min(old[1], new[1]),
                max(old[2], new[2]),
                max(old[3], new[3]),
            ]
        for row in rows:
            row["text"] = row["text"].strip()
            if row["runs"]:
                row["runs"][0]["text"] = row["runs"][0]["text"].lstrip()
                row["runs"][-1]["text"] = row["runs"][-1]["text"].rstrip()
        return rows
    finally:
        text_page.close()


def _visual_rows(items: list[dict[str, Any]], body_size: float) -> list[list[dict[str, Any]]]:
    """Group separated objects that share a visual baseline."""
    rows: list[list[dict[str, Any]]] = []
    for item in items:
        center = (item["bbox"][1] + item["bbox"][3]) / 2
        if rows:
            previous = rows[-1]
            previous_center = sum(
                (part["bbox"][1] + part["bbox"][3]) / 2 for part in previous
            ) / len(previous)
            if abs(center - previous_center) <= body_size * 0.45:
                previous.append(item)
                continue
        rows.append([item])
    return rows


def _content(
    item: dict[str, Any], *, styled: bool = True, suppress_italic: bool = False
) -> list[dict[str, Any]]:
    if not styled:
        return [{"type": "text", "text": item["text"].strip()}]
    result: list[dict[str, Any]] = []
    normal_centers = [
        (run["bbox"][1] + run["bbox"][3]) / 2
        for run in item["runs"]
        if run["size"] >= item["size"] * 0.9 and len(run["text"].strip()) > 1
    ]
    baseline_center = statistics.median(normal_centers) if normal_centers else None

    def append(node: dict[str, Any]) -> None:
        if result and result[-1]["type"] == node["type"] == "text":
            result[-1]["text"] += node["text"]
        else:
            result.append(node)

    for run in item["runs"]:
        raw_text = run["text"]
        if not raw_text:
            continue
        decorated = bool(
            run["bold"]
            or run["italic"]
            or run.get("underline")
            or run.get("highlight")
            or run.get("url")
            or (baseline_center is not None and run["size"] <= item["size"] * 0.8)
        )
        leading = raw_text[: len(raw_text) - len(raw_text.lstrip())] if decorated else ""
        trailing = raw_text[len(raw_text.rstrip()) :] if decorated else ""
        text = raw_text.strip() if decorated else raw_text
        if leading:
            append({"type": "text", "text": leading})
        if not text:
            continue
        node: dict[str, Any] = {"type": "text", "text": text}
        if baseline_center is not None and run["size"] <= item["size"] * 0.8:
            center = (run["bbox"][1] + run["bbox"][3]) / 2
            kind = "superscript" if center < baseline_center else "subscript"
            node = {"type": kind, "children": [node]}
        elif run["italic"] and not suppress_italic:
            node = {"type": "emphasis", "children": [node]}
        if run["bold"]:
            node = {"type": "strong", "children": [node]}
        if run.get("underline"):
            node = {"type": "underline", "children": [node]}
        if run.get("highlight"):
            node = {"type": "highlight", "children": [node]}
        if run.get("url"):
            node = {"type": "link", "url": run["url"], "children": [node]}
        append(node)
        if trailing:
            append({"type": "text", "text": trailing})
    return result


def _join_lines(first: dict[str, Any], following: dict[str, Any]) -> None:
    separator = "" if first["text"].endswith((" ", "-")) else " "
    first["text"] += separator + following["text"]
    runs = following["runs"]
    if runs and separator:
        runs[0] = {**runs[0], "text": separator + runs[0]["text"]}
    first["runs"].extend(runs)
    first["bbox"][2] = max(first["bbox"][2], following["bbox"][2])
    first["bbox"][3] = following["bbox"][3]


def _heading_levels(rows: list[list[dict[str, Any]]], body_size: float) -> dict[float, int]:
    sizes = sorted(
        {
            round(row[0]["size"], 1)
            for row in rows
            if len(row) == 1 and row[0]["size"] >= body_size * 1.3 and len(row[0]["text"]) <= 180
        },
        reverse=True,
    )
    return {size: min(index + 1, 6) for index, size in enumerate(sizes)}


def _is_simple_table(rows: list[list[dict[str, Any]]], start: int, body_size: float) -> int:
    width = len(rows[start])
    if width < 2:
        return 0
    reference = [item["bbox"][0] for item in rows[start]]
    end = start
    while end < len(rows) and len(rows[end]) == width:
        positions = [item["bbox"][0] for item in rows[end]]
        if any(
            abs(left - expected) > body_size * 2
            for left, expected in zip(positions, reference, strict=True)
        ):
            break
        end += 1
    return end - start if end - start >= 3 else 0


def _unordered_list_height(
    rows: list[list[dict[str, Any]]], start: int, body_size: float, left_margin: float
) -> int:
    if len(rows[start]) != 1:
        return 0
    first = rows[start][0]
    if first["bbox"][0] - left_margin < body_size or first["size"] > body_size * 1.12:
        return 0
    end = start + 1
    previous = first
    while end < len(rows) and len(rows[end]) == 1:
        item = rows[end][0]
        gap = item["bbox"][1] - previous["bbox"][1]
        if (
            abs(item["bbox"][0] - first["bbox"][0]) > body_size * 0.4
            or item["size"] > body_size * 1.12
            or gap > body_size * 1.6
            or re.match(r"^\d+[.)]\s*", item["text"])
        ):
            break
        previous = item
        end += 1
    return end - start if end - start >= 3 else 0


def extract_text_pdf(path: Path, start: int = 1, end: int | None = None) -> dict[str, Any]:
    document = pdfium.PdfDocument(path)
    try:
        pages = list(_range(document, start, end))
        objects = [_objects(document[number]) for number in pages]
        sizes = [item["size"] for page in objects for item in page]
        body_size = statistics.median(sizes) if sizes else 11.0
        blocks = []
        all_rows = [_visual_rows(page, body_size) for page in objects]
        heading_levels = _heading_levels([row for page in all_rows for row in page], body_size)
        ordered = re.compile(r"^(\d+)[.)]\s*(.+)$")
        for page_index, rows in enumerate(all_rows):
            if page_index:
                blocks.append({"type": "page_break"})
            left_margin = min(
                (
                    row[0]["bbox"][0]
                    for row in rows
                    if len(row) == 1 and row[0]["size"] <= body_size * 1.12
                ),
                default=0.0,
            )
            index = 0
            while index < len(rows):
                row = rows[index]
                table_height = _is_simple_table(rows, index, body_size)
                if table_height:
                    table_rows = rows[index : index + table_height]
                    blocks.append(
                        {
                            "type": "table",
                            "headers": [_content(item, styled=False) for item in table_rows[0]],
                            "rows": [
                                [_content(item) for item in table_row]
                                for table_row in table_rows[1:]
                            ],
                        }
                    )
                    index += table_height
                    continue
                if len(row) != 1:
                    value = " ".join(item["text"] for item in row)
                    blocks.append(
                        {"type": "paragraph", "content": [{"type": "text", "text": value}]}
                    )
                    index += 1
                    continue
                item = row[0]
                level = heading_levels.get(round(item["size"], 1))
                if level is not None:
                    blocks.append(
                        {"type": "heading", "level": level, "content": _content(item, styled=False)}
                    )
                    index += 1
                    continue
                unordered_height = _unordered_list_height(rows, index, body_size, left_margin)
                if unordered_height:
                    blocks.append(
                        {
                            "type": "list",
                            "ordered": False,
                            "items": [
                                {"content": _content(rows[row_index][0])}
                                for row_index in range(index, index + unordered_height)
                            ],
                        }
                    )
                    index += unordered_height
                    continue
                match = ordered.match(item["text"])
                if match:
                    items = []
                    expected = int(match.group(1))
                    while index < len(rows) and len(rows[index]) == 1:
                        candidate = ordered.match(rows[index][0]["text"])
                        if candidate is None or int(candidate.group(1)) != expected:
                            break
                        items.append(
                            {"content": [{"type": "text", "text": candidate.group(2).strip()}]}
                        )
                        expected += 1
                        index += 1
                    if len(items) >= 2:
                        blocks.append(
                            {
                                "type": "list",
                                "ordered": True,
                                "start": int(match.group(1)),
                                "items": items,
                            }
                        )
                        continue
                    index -= len(items)
                if item["runs"] and all(run["monospace"] for run in item["runs"]):
                    lines = []
                    while index < len(rows) and len(rows[index]) == 1:
                        candidate = rows[index][0]
                        if not candidate["runs"] or not all(
                            run["monospace"] for run in candidate["runs"]
                        ):
                            break
                        lines.append(candidate["text"])
                        index += 1
                    blocks.append({"type": "code_block", "text": "\n".join(lines)})
                    continue
                while index + 1 < len(rows) and len(rows[index + 1]) == 1:
                    following = rows[index + 1][0]
                    gap = following["bbox"][1] - item["bbox"][3]
                    aligned = abs(following["bbox"][0] - item["bbox"][0]) <= body_size * 0.4
                    if (
                        gap > body_size * 0.7
                        or not aligned
                        or heading_levels.get(round(following["size"], 1)) is not None
                        or ordered.match(following["text"])
                        or (
                            following["runs"] and all(run["monospace"] for run in following["runs"])
                        )
                    ):
                        break
                    _join_lines(item, following)
                    index += 1
                is_quote = (
                    item["bbox"][0] - left_margin >= body_size * 0.75
                    and item["bbox"][0] - left_margin <= body_size * 3
                    and len(item["text"]) >= 40
                    and item["runs"]
                    and all(run["italic"] for run in item["runs"] if run["text"].strip())
                )
                blocks.append(
                    {
                        "type": "quote" if is_quote else "paragraph",
                        "content": _content(item, suppress_italic=is_quote),
                    }
                )
                index += 1
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
                evidence = {
                    "page": number + 1,
                    "bbox": [round(float(value), 2) for value in item["bbox"]],
                    "page_size": [round(width, 2), round(height, 2)],
                    "text": item["text"],
                }
                urls = list(dict.fromkeys(run["url"] for run in item["runs"] if run.get("url")))
                if urls:
                    evidence["urls"] = urls
                result.append(evidence)
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
