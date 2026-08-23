"""Permissively licensed PDFium backend for extraction and rendering."""

from __future__ import annotations

import ctypes
import hashlib
import json
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
            action_type = pdfium.raw.FPDFAction_GetType(action) if action else 0
            url = None
            if action and action_type == pdfium.raw.PDFACTION_URI:
                length = pdfium.raw.FPDFAction_GetURIPath(page.pdf.raw, action, None, 0)
                if length <= 1 or length > 65_536:
                    continue
                buffer = ctypes.create_string_buffer(length)
                if not pdfium.raw.FPDFAction_GetURIPath(page.pdf.raw, action, buffer, length):
                    continue
                url = buffer.value.decode("utf-8", errors="replace")
            elif action and action_type == pdfium.raw.PDFACTION_GOTO:
                destination = pdfium.raw.FPDFAction_GetDest(page.pdf.raw, action)
                target = pdfium.raw.FPDFDest_GetDestPageIndex(page.pdf.raw, destination)
                if target >= 0:
                    url = f"#page-{target + 1}"
            if url is None:
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
                    "url": url,
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


def _drop_out_of_range_internal_links(objects: list[list[dict[str, Any]]], pages: list[int]) -> int:
    """Remove links whose generated page anchor cannot exist in the selected range."""
    selected = {number + 1 for number in pages}
    dropped = 0
    for page in objects:
        for item in page:
            for run in item["runs"]:
                match = re.fullmatch(r"#page-(\d+)", run.get("url", ""))
                if match and int(match.group(1)) not in selected:
                    run.pop("url")
                    dropped += 1
    return dropped


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
        return _column_major_order(rows, page.get_width())
    finally:
        text_page.close()


def _column_major_order(items: list[dict[str, Any]], page_width: float) -> list[dict[str, Any]]:
    """Use column-major order only when two or three substantial columns are evident."""

    def key(item: dict[str, Any]) -> tuple[float, float]:
        return item["bbox"][1], item["bbox"][0]

    def attempt(
        zones: list[tuple[float, float]], minimum_width: float
    ) -> list[dict[str, Any]] | None:
        evidence = [
            [
                item
                for item in items
                if item["bbox"][0] >= left
                and item["bbox"][2] <= right
                and item["bbox"][2] - item["bbox"][0] >= minimum_width
            ]
            for left, right in zones
        ]
        if any(len(column) < 2 for column in evidence):
            return None
        band_top = max(min(item["bbox"][1] for item in column) for column in evidence)
        band_bottom = min(max(item["bbox"][3] for item in column) for column in evidence)
        if band_bottom <= band_top:
            return None
        before = [item for item in items if item["bbox"][3] < band_top]
        columns = []
        for column_number, (left, right) in enumerate(zones):
            column = [
                item
                for item in items
                if item["bbox"][1] <= band_bottom
                and item["bbox"][0] >= left
                and item["bbox"][2] <= right
                and item not in before
            ]
            for item in column:
                item["_column"] = column_number
            columns.append(column)
        used = {id(item) for item in before + [item for column in columns for item in column]}
        after = [item for item in items if id(item) not in used]
        return (
            sorted(before, key=key)
            + [item for column in columns for item in sorted(column, key=key)]
            + sorted(after, key=key)
        )

    three = attempt(
        [
            (0, page_width * 0.31),
            (page_width * 0.345, page_width * 0.655),
            (page_width * 0.69, page_width),
        ],
        page_width * 0.12,
    )
    if three is not None:
        return three
    two = attempt([(0, page_width * 0.47), (page_width * 0.53, page_width)], page_width * 0.18)
    return two if two is not None else items


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


def _furniture_key(row: list[dict[str, Any]], page_height: float) -> str | None:
    top = min(item["bbox"][1] for item in row)
    bottom = max(item["bbox"][3] for item in row)
    if top > page_height * 0.12 and bottom < page_height * 0.88:
        return None
    text = " ".join(item["text"].strip() for item in row if item["text"].strip())
    if not text:
        return None
    normalized = re.sub(r"\b(?:page\s+)?\d+\b", "<page>", text.casefold()).strip()
    region = "top" if top <= page_height * 0.12 else "bottom"
    return f"{region}:{normalized}"


def _repeated_furniture(
    rows_by_page: list[list[list[dict[str, Any]]]], page_heights: list[float]
) -> set[str]:
    pages_by_key: dict[str, set[int]] = {}
    for page_index, rows in enumerate(rows_by_page):
        for row in rows:
            if key := _furniture_key(row, page_heights[page_index]):
                pages_by_key.setdefault(key, set()).add(page_index)
    return {key for key, pages in pages_by_key.items() if len(pages) >= 2}


def _footnote_definitions(
    rows: list[list[dict[str, Any]]], page_height: float, body_size: float
) -> tuple[dict[str, str], dict[str, set[int]]]:
    definitions = {}
    definition_rows: dict[str, set[int]] = {}
    for index, row in enumerate(rows):
        if len(row) != 1 or row[0]["bbox"][1] < page_height * 0.72:
            continue
        match = re.match(r"^(\d{1,3})[.)]?\s+(.{3,})$", row[0]["text"].strip())
        if match:
            parts = [match.group(2).strip()]
            rows_for_definition = {id(row)}
            previous = row[0]
            for following_row in rows[index + 1 :]:
                if len(following_row) != 1:
                    break
                following = following_row[0]
                gap = following["bbox"][1] - previous["bbox"][3]
                if (
                    gap < 0
                    or gap > body_size * 0.8
                    or abs(following["bbox"][0] - row[0]["bbox"][0]) > body_size * 2
                ):
                    break
                parts.append(following["text"].strip())
                rows_for_definition.add(id(following_row))
                previous = following
            definitions[match.group(1)] = " ".join(parts)
            definition_rows[match.group(1)] = rows_for_definition
    return definitions, definition_rows


def _footnote_references(items: list[dict[str, Any]]) -> set[str]:
    """Return numeric labels carried by clearly raised, smaller text runs."""
    labels = set()
    for item in items:
        normal_centers = [
            (run["bbox"][1] + run["bbox"][3]) / 2
            for run in item["runs"]
            if run["size"] >= item["size"] * 0.9 and len(run["text"].strip()) > 1
        ]
        if not normal_centers:
            continue
        baseline_center = statistics.median(normal_centers)
        for run in item["runs"]:
            label = run["text"].strip()
            center = (run["bbox"][1] + run["bbox"][3]) / 2
            if (
                re.fullmatch(r"\d{1,3}", label)
                and run["size"] <= item["size"] * 0.8
                and center < baseline_center
            ):
                labels.add(label)
    return labels


def _content(
    item: dict[str, Any],
    *,
    styled: bool = True,
    suppress_italic: bool = False,
    footnotes: dict[str, str] | None = None,
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
            if kind == "superscript" and footnotes and text.strip() in footnotes:
                node = {
                    "type": "footnote",
                    "children": [{"type": "text", "text": footnotes[text.strip()]}],
                }
            else:
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
            abs(left - expected) > body_size * 2.5
            for left, expected in zip(positions, reference, strict=True)
        ):
            break
        end += 1
    return end - start if end - start >= 3 else 0


def _enclosing_cell(item: dict[str, Any], paths: list[list[float]]) -> list[float] | None:
    candidates = [
        path
        for path in paths
        if _inside(item["bbox"], path, tolerance=1.5)
        and path[2] - path[0] > item["bbox"][2] - item["bbox"][0] + 2
        and path[3] - path[1] > item["bbox"][3] - item["bbox"][1] + 2
    ]
    return (
        min(candidates, key=lambda path: (path[2] - path[0]) * (path[3] - path[1]))
        if candidates
        else None
    )


def _bordered_spanning_table(
    rows: list[list[dict[str, Any]]], start: int, body_size: float, paths: list[list[float]]
) -> tuple[int, dict[str, Any]] | None:
    if len(rows[start]) < 2:
        return None
    candidate_rows = []
    index = start
    previous_bottom = None
    while index < len(rows):
        row = rows[index]
        if (
            previous_bottom is not None
            and min(item["bbox"][1] for item in row) - previous_bottom > body_size * 2.5
        ):
            break
        regions = [_enclosing_cell(item, paths) for item in row]
        if any(region is None for region in regions):
            break
        candidate_rows.append((row, regions))
        previous_bottom = max(item["bbox"][3] for item in row)
        index += 1
    if len(candidate_rows) < 3:
        return None
    header, header_regions = candidate_rows[0]
    if len(header_regions) != len(header):
        return None
    header_regions = sorted(header_regions, key=lambda region: region[0])  # type: ignore[index]
    centers = [(region[0] + region[2]) / 2 for region in header_regions]  # type: ignore[index]
    row_centers = [
        sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in row) / len(row)
        for row, _ in candidate_rows
    ]
    body_rows = []
    found_span = False
    for row_index, (row, regions) in enumerate(candidate_rows[1:], 1):
        cells = []
        for item, region in sorted(zip(row, regions, strict=True), key=lambda pair: pair[1][0]):  # type: ignore[index]
            assert region is not None
            columns = [
                column for column, center in enumerate(centers) if region[0] <= center <= region[2]
            ]
            if not columns:
                return None
            colspan = len(columns)
            rowspan = sum(
                1 for center in row_centers[row_index:] if region[1] <= center <= region[3]
            )
            cell: Any = _content(item)
            if rowspan > 1 or colspan > 1:
                found_span = True
                cell = {"content": cell}
                if rowspan > 1:
                    cell["rowspan"] = rowspan
                if colspan > 1:
                    cell["colspan"] = colspan
            cells.append((columns[0], cell))
        body_rows.append([cell for _, cell in sorted(cells)])
    if not found_span:
        return None
    return len(candidate_rows), {
        "type": "table",
        "headers": [_content(item, styled=False) for item in header],
        "alignments": _table_alignments([row for row, _ in candidate_rows], body_size)
        if all(len(row) == len(header) for row, _ in candidate_rows)
        else ["left"] * len(header),
        "rows": body_rows,
    }


def _table_alignments(rows: list[list[dict[str, Any]]], body_size: float) -> list[str]:
    """Infer column alignment only when one geometric edge is clearly more stable."""
    result = []
    for column in zip(*rows, strict=True):
        lefts = [item["bbox"][0] for item in column]
        rights = [item["bbox"][2] for item in column]
        centers = [(left + right) / 2 for left, right in zip(lefts, rights, strict=True)]
        spreads = {
            "left": max(lefts) - min(lefts),
            "right": max(rights) - min(rights),
            "center": max(centers) - min(centers),
        }
        best = min(spreads, key=spreads.get)  # type: ignore[arg-type]
        alternatives = sorted(spreads.values())
        confident = (
            alternatives[0] <= body_size * 0.4
            and alternatives[1] - alternatives[0] >= body_size * 0.25
        )
        result.append(best if confident else "left")
    return result


def _inside(inner: list[float], outer: list[float], tolerance: float = 1.0) -> bool:
    return (
        inner[0] >= outer[0] - tolerance
        and inner[1] >= outer[1] - tolerance
        and inner[2] <= outer[2] + tolerance
        and inner[3] <= outer[3] + tolerance
    )


def _vector_figure_regions(
    page: pdfium.PdfPage,
    items: list[dict[str, Any]],
    body_size: float,
    output_dir: Path | None,
    page_number: int,
) -> list[dict[str, Any]]:
    """Preserve obvious multi-part vector artwork as cropped local PNG figures."""
    if output_dir is None:
        return []
    page_width, _ = page.get_size()
    paths = _page_paths(page)
    candidates = []
    for bounds in paths:
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        enclosed = [path for path in paths if _inside(path, bounds)]
        labels = [item for item in items if _inside(item["bbox"], bounds)]
        if (
            width >= page_width * 0.35
            and height >= body_size * 4
            and len(enclosed) >= 5
            and len(labels) >= 2
            and not all(label["monospace"] for label in labels)
        ):
            candidates.append((bounds, labels))
    # Keep outer regions only; nested paths are components of the same figure.
    regions = [
        candidate
        for candidate in candidates
        if not any(
            candidate[0] != other[0] and _inside(candidate[0], other[0]) for other in candidates
        )
    ]
    if not regions:
        return []
    output_dir.mkdir(parents=True, exist_ok=True)
    bitmap = page.render(scale=2, rev_byteorder=True)
    try:
        page_image = bitmap.to_pil().convert("RGB")
    finally:
        bitmap.close()
    result = []
    for figure_number, (bounds, labels) in enumerate(regions, 1):
        padding = body_size * 0.3
        crop = [
            max(0, int((bounds[0] - padding) * 2)),
            max(0, int((bounds[1] - padding) * 2)),
            min(page_image.width, int((bounds[2] + padding) * 2 + 0.999)),
            min(page_image.height, int((bounds[3] + padding) * 2 + 0.999)),
        ]
        target = output_dir / f"page-{page_number}-vector-{figure_number}.png"
        page_image.crop(tuple(crop)).save(target)
        alt = ", ".join(label["text"].strip() for label in labels if label["text"].strip())
        result.append(
            {
                "bbox": bounds,
                "block": {"type": "figure", "src": f"{output_dir.name}/{target.name}", "alt": alt},
            }
        )
    return result


def _raster_figure_regions(
    page: pdfium.PdfPage,
    output_dir: Path | None,
    page_number: int,
    assets: dict[str, Path],
) -> list[dict[str, Any]]:
    """Extract each placed raster object together with its document position."""
    if output_dir is None:
        return []
    output_dir.mkdir(parents=True, exist_ok=True)
    height = page.get_height()
    result = []
    for figure_number, item in enumerate(
        page.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,), max_depth=8), 1
    ):
        left, bottom, right, top = item.get_bounds()
        bitmap = item.get_bitmap(render=True, scale_to_original=True)
        try:
            image = bitmap.to_pil().convert("RGB")
        finally:
            bitmap.close()
        digest = hashlib.sha256(image.tobytes()).hexdigest()
        target = assets.get(digest)
        if target is None:
            target = output_dir / f"page-{page_number}-raster-{figure_number}.png"
            image.save(target)
            assets[digest] = target
        result.append(
            {
                "bbox": [left, height - top, right, height - bottom],
                "block": {"type": "figure", "src": f"{output_dir.name}/{target.name}", "alt": ""},
            }
        )
    return result


def _attach_figure_captions(
    figures: list[dict[str, Any]], rows: list[list[dict[str, Any]]], body_size: float
) -> set[int]:
    consumed: set[int] = set()
    for figure in figures:
        bottom = figure["bbox"][3]
        candidates = [
            row
            for row in rows
            if id(row) not in consumed
            and len(row) == 1
            and 0 <= row[0]["bbox"][1] - bottom <= body_size * 1.8
        ]
        if not candidates:
            continue
        row = min(candidates, key=lambda value: value[0]["bbox"][1])
        item = row[0]
        is_caption = bool(re.match(r"^(?:figure|fig\.)\s*\d*\s*[:.]", item["text"], re.I)) or (
            item["runs"] and all(run["italic"] for run in item["runs"] if run["text"].strip())
        )
        if is_caption:
            figure["block"]["caption"] = _content(item, suppress_italic=True)
            consumed.add(id(row))
    return consumed


def _infer_code_language(text: str) -> str | None:
    """Return a language only for combinations of strongly identifying syntax."""
    if re.search(r"<\?php\b", text, re.I) or (
        re.search(r"\$[A-Za-z_]\w*", text)
        and re.search(r"\b(?:function|class|namespace|use)\b|->|::", text)
    ):
        return "php"
    if re.search(r"^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\([^\n]*\)\s*:", text, re.M):
        return "python"
    if re.search(r"\b(?:const|let|var)\s+[A-Za-z_$]", text) and re.search(
        r"=>|\b(?:function|import|export)\b", text
    ):
        return "javascript"
    if re.search(r"^\s*SELECT\b", text, re.I | re.M) and re.search(r"\bFROM\b", text, re.I):
        return "sql"
    if text.startswith("#!") and re.search(r"\b(?:ba|z|fi)?sh\b", text.splitlines()[0]):
        return "bash"
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    else:
        if isinstance(parsed, (dict, list)):
            return "json"
    return None


def _contains_inline(value: Any, kind: str) -> bool:
    if isinstance(value, list):
        return any(_contains_inline(item, kind) for item in value)
    if not isinstance(value, dict):
        return False
    return value.get("type") == kind or any(_contains_inline(item, kind) for item in value.values())


def _contains_internal_link(value: Any) -> bool:
    if isinstance(value, list):
        return any(_contains_internal_link(item) for item in value)
    if not isinstance(value, dict):
        return False
    return bool(re.fullmatch(r"#page-\d+", value.get("url", ""))) or any(
        _contains_internal_link(item) for item in value.values()
    )


def _inference_provenance(
    blocks: list[dict[str, Any]], first_page: int = 1
) -> list[dict[str, Any]]:
    result = []
    page = first_page
    for index, block in enumerate(blocks):
        if block["type"] == "page_break":
            page += 1
            continue
        warnings = []
        if block["type"] == "code_block" and block.get("language"):
            warnings.append("code language inferred from strongly identifying syntax")
        if block["type"] == "table":
            if any(value != "left" for value in block.get("alignments", [])):
                warnings.append("table alignment inferred from stable visual edges")
            if block.get("caption"):
                warnings.append("table caption associated by proximity and explicit label")
        if block["type"] == "figure":
            kind = "vector crop" if "-vector-" in block["src"] else "placed raster object"
            warnings.append(f"figure preserved from {kind}")
            if block.get("caption"):
                warnings.append("figure caption associated by proximity and explicit styling")
        if _contains_inline(block, "footnote"):
            warnings.append("footnote paired from superscript reference and bottom definition")
        if _contains_internal_link(block):
            warnings.append("internal link resolved to a generated page heading anchor")
        if block.get("id", "").startswith("page-"):
            warnings.append("page heading anchor generated for an internal PDF destination")
        if warnings:
            result.append(
                {
                    "block": index,
                    "page": page,
                    "confidence": 0.9,
                    "warnings": warnings,
                }
            )
    return result


def _merge_continued_tables(blocks: list[dict[str, Any]]) -> int:
    merged = 0
    index = 0
    while index + 2 < len(blocks):
        first, boundary, following = blocks[index : index + 3]
        if (
            first["type"] == following["type"] == "table"
            and boundary["type"] == "page_break"
            and first["headers"] == following["headers"]
            and first.get("alignments") == following.get("alignments")
        ):
            first["rows"].extend(following["rows"])
            if "caption" not in first and "caption" in following:
                first["caption"] = following["caption"]
            del blocks[index + 1 : index + 3]
            merged += 1
            continue
        index += 1
    return merged


def _anchor_unheaded_target_pages(
    blocks: list[dict[str, Any]], target_pages: set[int], anchored_pages: set[int], first_page: int
) -> None:
    page = first_page
    for block in blocks:
        if block["type"] == "page_break":
            page += 1
            continue
        if page in target_pages and page not in anchored_pages and block["type"] == "paragraph":
            block["id"] = f"page-{page}"
            anchored_pages.add(page)


def _unordered_list_height(
    rows: list[list[dict[str, Any]]], start: int, body_size: float, left_margin: float
) -> int:
    if len(rows[start]) != 1:
        return 0
    first = rows[start][0]
    if first.get("_column", 0) > 0:
        return 0
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


def extract_text_pdf(
    path: Path, start: int = 1, end: int | None = None, assets_dir: Path | None = None
) -> dict[str, Any]:
    document = pdfium.PdfDocument(path)
    try:
        pages = list(_range(document, start, end))
        objects = [_objects(document[number]) for number in pages]
        dropped_internal_links = _drop_out_of_range_internal_links(objects, pages)
        sizes = [
            item["size"]
            for index, page in enumerate(objects)
            for item in page
            if document[pages[index]].get_height() * 0.12
            <= (item["bbox"][1] + item["bbox"][3]) / 2
            <= document[pages[index]].get_height() * 0.88
        ]
        body_size = statistics.median(sizes) if sizes else 11.0
        blocks = []
        all_rows = [_visual_rows(page, body_size) for page in objects]
        paths_by_page = [_page_paths(document[number]) for number in pages]
        page_heights = [document[number].get_height() for number in pages]
        repeated_furniture = _repeated_furniture(all_rows, page_heights)
        page_footnotes = [
            _footnote_definitions(rows, page_heights[index], body_size)
            for index, rows in enumerate(all_rows)
        ]
        referenced_footnotes = {label for page in objects for label in _footnote_references(page)}
        footnote_counts: dict[str, int] = {}
        for definitions, _ in page_footnotes:
            for label in definitions:
                footnote_counts[label] = footnote_counts.get(label, 0) + 1
        document_footnotes = {
            label: text
            for definitions, _ in page_footnotes
            for label, text in definitions.items()
            if footnote_counts[label] == 1 and label in referenced_footnotes
        }
        column_pages = {
            pages[index] + 1: max(item.get("_column", 0) for item in page) + 1
            for index, page in enumerate(objects)
            if any("_column" in item for item in page)
        }
        raster_assets: dict[str, Path] = {}
        figure_regions = [
            sorted(
                _vector_figure_regions(
                    document[number], objects[index], body_size, assets_dir, number + 1
                )
                + _raster_figure_regions(document[number], assets_dir, number + 1, raster_assets),
                key=lambda region: (region["bbox"][1], region["bbox"][0]),
            )
            for index, number in enumerate(pages)
        ]
        heading_levels = _heading_levels([row for page in all_rows for row in page], body_size)
        target_pages = {
            int(run["url"].removeprefix("#page-"))
            for page in objects
            for item in page
            for run in item["runs"]
            if re.fullmatch(r"#page-\d+", run.get("url", ""))
        }
        anchored_pages: set[int] = set()
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
            emitted_figures: set[int] = set()
            footnotes = document_footnotes
            footnote_rows = {
                row
                for label, rows_for_definition in page_footnotes[page_index][1].items()
                if label in document_footnotes
                for row in rows_for_definition
            }
            caption_rows = _attach_figure_captions(figure_regions[page_index], rows, body_size)
            while index < len(rows):
                row = rows[index]
                if id(row) in caption_rows or id(row) in footnote_rows:
                    index += 1
                    continue
                row_top = min(item["bbox"][1] for item in row)
                for figure_index, region in enumerate(figure_regions[page_index]):
                    if figure_index not in emitted_figures and region["bbox"][3] < row_top:
                        blocks.append(region["block"])
                        emitted_figures.add(figure_index)
                if _furniture_key(row, page_heights[page_index]) in repeated_furniture:
                    index += 1
                    continue
                figure = next(
                    (
                        region
                        for region in figure_regions[page_index]
                        if any(_inside(item["bbox"], region["bbox"]) for item in row)
                    ),
                    None,
                )
                if figure is not None:
                    figure_index = figure_regions[page_index].index(figure)
                    if figure_index not in emitted_figures:
                        blocks.append(figure["block"])
                        emitted_figures.add(figure_index)
                    index += 1
                    continue
                table_height = _is_simple_table(rows, index, body_size)
                if table_height:
                    table_rows = rows[index : index + table_height]
                    table = {
                        "type": "table",
                        "headers": [_content(item, styled=False) for item in table_rows[0]],
                        "alignments": _table_alignments(table_rows, body_size),
                        "rows": [
                            [_content(item, footnotes=footnotes) for item in table_row]
                            for table_row in table_rows[1:]
                        ],
                    }
                    caption_index = index + table_height
                    if caption_index < len(rows) and len(rows[caption_index]) == 1:
                        caption = rows[caption_index][0]
                        gap = caption["bbox"][1] - max(item["bbox"][3] for item in table_rows[-1])
                        if gap <= body_size * 1.8 and re.match(
                            r"^table\s*\d*\s*[:.]", caption["text"], re.I
                        ):
                            table["caption"] = _content(caption, suppress_italic=True)
                            table_height += 1
                    blocks.append(table)
                    index += table_height
                    continue
                spanning = _bordered_spanning_table(
                    rows, index, body_size, paths_by_page[page_index]
                )
                if spanning is not None:
                    table_height, table = spanning
                    blocks.append(table)
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
                    heading = {
                        "type": "heading",
                        "level": level,
                        "content": _content(item, styled=False),
                    }
                    page_number = pages[page_index] + 1
                    if page_number in target_pages and page_number not in anchored_pages:
                        heading["id"] = f"page-{page_number}"
                        anchored_pages.add(page_number)
                    blocks.append(heading)
                    index += 1
                    continue
                unordered_height = _unordered_list_height(rows, index, body_size, left_margin)
                if unordered_height:
                    blocks.append(
                        {
                            "type": "list",
                            "ordered": False,
                            "items": [
                                {"content": _content(rows[row_index][0], footnotes=footnotes)}
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
                    text = "\n".join(lines)
                    block = {"type": "code_block", "text": text}
                    if language := _infer_code_language(text):
                        block["language"] = language
                    blocks.append(block)
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
                        "content": _content(item, suppress_italic=is_quote, footnotes=footnotes),
                    }
                )
                index += 1
            for figure_index, region in enumerate(figure_regions[page_index]):
                if figure_index not in emitted_figures:
                    blocks.append(region["block"])
        _anchor_unheaded_target_pages(blocks, target_pages, anchored_pages, pages[0] + 1)
        merged_tables = _merge_continued_tables(blocks)
        metadata = document.get_metadata_dict()
        result: dict[str, Any] = {"version": 1, "blocks": blocks}
        provenance = _inference_provenance(blocks, pages[0] + 1)
        if provenance:
            result["provenance"] = provenance
        diagnostics = []
        if repeated_furniture:
            diagnostics.append(
                f"suppressed {len(repeated_furniture)} repeated header/footer pattern(s)"
            )
        diagnostics.extend(
            f"page {page}: {count}-column reading order inferred from stable gutters"
            for page, count in sorted(column_pages.items())
        )
        if merged_tables:
            diagnostics.append(f"merged {merged_tables} table continuation(s) across page breaks")
        if dropped_internal_links:
            diagnostics.append(
                f"dropped {dropped_internal_links} internal link run(s) whose destination "
                "was outside the selected page range"
            )
        if diagnostics:
            result["diagnostics"] = diagnostics
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
        pages = list(_range(document, start, end))
        objects = [_objects(document[number]) for number in pages]
        _drop_out_of_range_internal_links(objects, pages)
        result = []
        for number, page_objects in zip(pages, objects, strict=True):
            page = document[number]
            width, height = page.get_size()
            for item in page_objects:
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
