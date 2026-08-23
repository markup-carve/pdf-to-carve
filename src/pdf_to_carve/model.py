"""Small, provider-neutral document model and strict JSON validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class DocumentError(ValueError):
    """Raised when extracted document JSON does not match the contract."""


INLINE_TYPES = {
    "text",
    "strong",
    "emphasis",
    "underline",
    "strike",
    "highlight",
    "superscript",
    "subscript",
    "insert",
    "delete",
    "substitute",
    "footnote",
    "code",
    "math",
    "link",
}
BLOCK_TYPES = {
    "heading",
    "paragraph",
    "list",
    "code_block",
    "quote",
    "table",
    "figure",
    "admonition",
    "thematic_break",
    "page_break",
}


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DocumentError(f"{path} must be an object")
    return value


def _string(value: Any, path: str, *, empty: bool = True) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        qualifier = "a non-empty string" if not empty else "a string"
        raise DocumentError(f"{path} must be {qualifier}")
    return value


def _name(value: Any, path: str) -> str:
    name = _string(value, path, empty=False)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name):
        raise DocumentError(f"{path} must be a portable name")
    return name


def _keys(value: dict[str, Any], allowed: set[str], path: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise DocumentError(f"{path} has unknown field(s): {', '.join(extra)}")


@dataclass(frozen=True)
class Inline:
    type: str
    text: str = ""
    children: tuple[Inline, ...] = ()
    url: str | None = None
    replacement: tuple[Inline, ...] = ()

    @classmethod
    def from_json(cls, value: Any, path: str) -> Inline:
        obj = _object(value, path)
        kind = _string(obj.get("type"), f"{path}.type", empty=False)
        if kind not in INLINE_TYPES:
            raise DocumentError(f"{path}.type is not supported: {kind}")
        if kind in {"text", "code", "math"}:
            _keys(obj, {"type", "text"}, path)
            return cls(kind, text=_string(obj.get("text"), f"{path}.text"))
        if kind == "substitute":
            _keys(obj, {"type", "children", "replacement"}, path)
            replacement = _inlines(obj.get("replacement"), f"{path}.replacement")
            url = None
        elif kind == "link":
            _keys(obj, {"type", "children", "url"}, path)
            url = _string(obj.get("url"), f"{path}.url", empty=False)
            replacement = ()
        else:
            _keys(obj, {"type", "children"}, path)
            url = None
            replacement = ()
        raw_children = obj.get("children")
        if not isinstance(raw_children, list) or not raw_children:
            raise DocumentError(f"{path}.children must be a non-empty array")
        children = tuple(
            cls.from_json(item, f"{path}.children[{i}]") for i, item in enumerate(raw_children)
        )
        return cls(kind, children=children, url=url, replacement=replacement)


def _inlines(value: Any, path: str) -> tuple[Inline, ...]:
    if not isinstance(value, list):
        raise DocumentError(f"{path} must be an array")
    return tuple(Inline.from_json(item, f"{path}[{i}]") for i, item in enumerate(value))


def _table_cell(value: Any, path: str) -> dict[str, Any]:
    if isinstance(value, list):
        return {"content": _inlines(value, path), "rowspan": 1, "colspan": 1}
    obj = _object(value, path)
    _keys(obj, {"content", "rowspan", "colspan"}, path)
    rowspan = obj.get("rowspan", 1)
    colspan = obj.get("colspan", 1)
    if not isinstance(rowspan, int) or isinstance(rowspan, bool) or rowspan < 1:
        raise DocumentError(f"{path}.rowspan must be a positive integer")
    if not isinstance(colspan, int) or isinstance(colspan, bool) or colspan < 1:
        raise DocumentError(f"{path}.colspan must be a positive integer")
    return {
        "content": _inlines(obj.get("content"), f"{path}.content"),
        "rowspan": rowspan,
        "colspan": colspan,
    }


def _validate_table_grid(rows: list[list[dict[str, Any]]], width: int, path: str) -> None:
    occupied = [0] * width
    for y, row in enumerate(rows):
        active = [remaining > 0 for remaining in occupied]
        cursor = 0
        for x, cell in enumerate(row):
            while cursor < width and active[cursor]:
                cursor += 1
            end = cursor + cell["colspan"]
            if end > width or any(active[cursor:end]):
                raise DocumentError(f"{path}[{y}][{x}] does not fit the {width}-column grid")
            for column in range(cursor, end):
                active[column] = True
                occupied[column] = max(occupied[column], cell["rowspan"])
            cursor = end
        if not all(active):
            missing = sum(not column for column in active)
            raise DocumentError(f"{path}[{y}] leaves {missing} grid column(s) unaccounted for")
        occupied = [max(0, remaining - 1) for remaining in occupied]


@dataclass(frozen=True)
class Block:
    type: str
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, value: Any, path: str) -> Block:
        obj = _object(value, path)
        kind = _string(obj.get("type"), f"{path}.type", empty=False)
        if kind not in BLOCK_TYPES:
            raise DocumentError(f"{path}.type is not supported: {kind}")
        data: dict[str, Any]
        if kind == "heading":
            _keys(obj, {"type", "level", "content", "id"}, path)
            level = obj.get("level")
            if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 6:
                raise DocumentError(f"{path}.level must be an integer from 1 to 6")
            data = {"level": level, "content": _inlines(obj.get("content"), f"{path}.content")}
            if "id" in obj:
                data["id"] = _string(obj["id"], f"{path}.id", empty=False)
        elif kind == "paragraph":
            _keys(obj, {"type", "content"}, path)
            data = {"content": _inlines(obj.get("content"), f"{path}.content")}
        elif kind == "list":
            _keys(obj, {"type", "ordered", "start", "items"}, path)
            ordered = obj.get("ordered", False)
            if not isinstance(ordered, bool):
                raise DocumentError(f"{path}.ordered must be a boolean")
            start = obj.get("start", 1)
            if not isinstance(start, int) or isinstance(start, bool) or start < 1:
                raise DocumentError(f"{path}.start must be a positive integer")
            items = obj.get("items")
            if not isinstance(items, list) or not items:
                raise DocumentError(f"{path}.items must be a non-empty array")
            parsed = []
            task_state: bool | None = None
            for i, item in enumerate(items):
                item_obj = _object(item, f"{path}.items[{i}]")
                _keys(item_obj, {"content", "checked"}, f"{path}.items[{i}]")
                row = {"content": _inlines(item_obj.get("content"), f"{path}.items[{i}].content")}
                if "checked" in item_obj:
                    if not isinstance(item_obj["checked"], bool):
                        raise DocumentError(f"{path}.items[{i}].checked must be a boolean")
                    row["checked"] = item_obj["checked"]
                is_task = "checked" in item_obj
                if task_state is None:
                    task_state = is_task
                elif task_state != is_task:
                    raise DocumentError(f"{path}.items must not mix task and ordinary items")
                parsed.append(row)
            data = {"ordered": ordered, "start": start, "items": parsed}
        elif kind == "code_block":
            _keys(obj, {"type", "text", "language"}, path)
            data = {"text": _string(obj.get("text"), f"{path}.text")}
            if "language" in obj:
                data["language"] = _string(obj["language"], f"{path}.language")
        elif kind == "quote":
            _keys(obj, {"type", "content", "attribution"}, path)
            data = {"content": _inlines(obj.get("content"), f"{path}.content")}
            if "attribution" in obj:
                data["attribution"] = _inlines(obj["attribution"], f"{path}.attribution")
        elif kind == "table":
            _keys(obj, {"type", "headers", "rows", "alignments", "caption"}, path)
            headers = obj.get("headers")
            rows = obj.get("rows")
            if not isinstance(headers, list) or not headers:
                raise DocumentError(f"{path}.headers must be a non-empty array")
            if not isinstance(rows, list):
                raise DocumentError(f"{path}.rows must be an array")
            parsed_headers = [
                _inlines(cell, f"{path}.headers[{i}]") for i, cell in enumerate(headers)
            ]
            parsed_rows: list[list[dict[str, Any]]] = []
            for y, row in enumerate(rows):
                if not isinstance(row, list):
                    raise DocumentError(f"{path}.rows[{y}] must be an array")
                parsed_rows.append(
                    [_table_cell(cell, f"{path}.rows[{y}][{x}]") for x, cell in enumerate(row)]
                )
            _validate_table_grid(parsed_rows, len(headers), f"{path}.rows")
            data = {"headers": parsed_headers, "rows": parsed_rows}
            if "alignments" in obj:
                alignments = obj["alignments"]
                if not isinstance(alignments, list) or len(alignments) != len(headers):
                    raise DocumentError(f"{path}.alignments must have one entry per column")
                if any(value not in {"left", "right", "center"} for value in alignments):
                    raise DocumentError(f"{path}.alignments entries must be left, right, or center")
                data["alignments"] = tuple(alignments)
            if "caption" in obj:
                data["caption"] = _inlines(obj["caption"], f"{path}.caption")
        elif kind == "figure":
            _keys(obj, {"type", "src", "alt", "caption", "id"}, path)
            data = {
                "src": _string(obj.get("src"), f"{path}.src", empty=False),
                "alt": _string(obj.get("alt", ""), f"{path}.alt"),
            }
            if "caption" in obj:
                data["caption"] = _inlines(obj["caption"], f"{path}.caption")
            if "id" in obj:
                data["id"] = _string(obj["id"], f"{path}.id", empty=False)
        elif kind == "admonition":
            _keys(obj, {"type", "kind", "content", "title"}, path)
            data = {
                "kind": _name(obj.get("kind"), f"{path}.kind"),
                "content": _inlines(obj.get("content"), f"{path}.content"),
            }
            if "title" in obj:
                data["title"] = _inlines(obj["title"], f"{path}.title")
        else:
            _keys(obj, {"type"}, path)
            data = {}
        return cls(kind, data)


@dataclass(frozen=True)
class Provenance:
    block: int
    page: int
    bbox: tuple[float, float, float, float] | None = None
    confidence: float | None = None
    warnings: tuple[str, ...] = ()
    evidence: str | None = None

    @classmethod
    def from_json(cls, value: Any, path: str, block_count: int) -> Provenance:
        obj = _object(value, path)
        _keys(obj, {"block", "page", "bbox", "confidence", "warnings", "evidence"}, path)
        block = obj.get("block")
        page = obj.get("page")
        if not isinstance(block, int) or isinstance(block, bool) or not 0 <= block < block_count:
            raise DocumentError(f"{path}.block must identify an existing block")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise DocumentError(f"{path}.page must be a positive integer")
        bbox = None
        if "bbox" in obj:
            raw_bbox = obj["bbox"]
            if (
                not isinstance(raw_bbox, list)
                or len(raw_bbox) != 4
                or any(not isinstance(n, (int, float)) or isinstance(n, bool) for n in raw_bbox)
            ):
                raise DocumentError(f"{path}.bbox must contain four numbers")
            bbox = tuple(float(n) for n in raw_bbox)
            if bbox[2] < bbox[0] or bbox[3] < bbox[1]:
                raise DocumentError(f"{path}.bbox must have ordered coordinates")
        confidence = None
        if "confidence" in obj:
            raw_confidence = obj["confidence"]
            if (
                not isinstance(raw_confidence, (int, float))
                or isinstance(raw_confidence, bool)
                or not 0 <= raw_confidence <= 1
            ):
                raise DocumentError(f"{path}.confidence must be between 0 and 1")
            confidence = float(raw_confidence)
        raw_warnings = obj.get("warnings", [])
        if not isinstance(raw_warnings, list):
            raise DocumentError(f"{path}.warnings must be an array")
        warnings = tuple(
            _string(item, f"{path}.warnings[{i}]", empty=False)
            for i, item in enumerate(raw_warnings)
        )
        evidence = None
        if "evidence" in obj:
            evidence = _string(obj["evidence"], f"{path}.evidence")
        return cls(block, page, bbox, confidence, warnings, evidence)


@dataclass(frozen=True)
class Document:
    blocks: tuple[Block, ...]
    title: str | None = None
    author: str | None = None
    language: str | None = None
    provenance: tuple[Provenance, ...] = ()

    @classmethod
    def from_json(cls, value: Any) -> Document:
        obj = _object(value, "document")
        _keys(
            obj,
            {"version", "title", "author", "language", "blocks", "provenance"},
            "document",
        )
        if obj.get("version") != 1:
            raise DocumentError("document.version must be 1")
        raw_blocks = obj.get("blocks")
        if not isinstance(raw_blocks, list):
            raise DocumentError("document.blocks must be an array")
        metadata = {}
        for name in ("title", "author", "language"):
            if name in obj:
                metadata[name] = _string(obj[name], f"document.{name}", empty=False)
        blocks = tuple(
            Block.from_json(item, f"document.blocks[{i}]") for i, item in enumerate(raw_blocks)
        )
        raw_provenance = obj.get("provenance", [])
        if not isinstance(raw_provenance, list):
            raise DocumentError("document.provenance must be an array")
        provenance = tuple(
            Provenance.from_json(item, f"document.provenance[{i}]", len(blocks))
            for i, item in enumerate(raw_provenance)
        )
        if len({entry.block for entry in provenance}) != len(provenance):
            raise DocumentError("document.provenance must contain at most one entry per block")
        return cls(blocks=blocks, provenance=provenance, **metadata)


def document_to_json(document: Document) -> dict[str, Any]:
    """Return the public extraction shape, suitable for saving and replaying."""

    def inline(node: Inline) -> dict[str, Any]:
        result: dict[str, Any] = {"type": node.type}
        if node.type in {"text", "code", "math"}:
            result["text"] = node.text
        else:
            result["children"] = [inline(child) for child in node.children]
            if node.type == "link":
                result["url"] = node.url
            if node.type == "substitute":
                result["replacement"] = [inline(child) for child in node.replacement]
        return result

    def value(item: Any) -> Any:
        if isinstance(item, Inline):
            return inline(item)
        if isinstance(item, tuple):
            return [value(entry) for entry in item]
        if isinstance(item, list):
            return [value(entry) for entry in item]
        if isinstance(item, dict):
            return {key: value(entry) for key, entry in item.items()}
        return item

    result: dict[str, Any] = {"version": 1, "blocks": []}
    for name in ("title", "author", "language"):
        if (entry := getattr(document, name)) is not None:
            result[name] = entry
    rendered_blocks = []
    for block in document.blocks:
        rendered = {"type": block.type, **value(block.data)}
        if block.type == "list" and rendered.get("start") == 1:
            rendered.pop("start")
        if block.type == "table":
            rendered["rows"] = []
            for row in block.data["rows"]:
                cells = []
                for cell in row:
                    content = value(cell["content"])
                    if cell["rowspan"] == 1 and cell["colspan"] == 1:
                        cells.append(content)
                    else:
                        entry = {"content": content}
                        if cell["rowspan"] != 1:
                            entry["rowspan"] = cell["rowspan"]
                        if cell["colspan"] != 1:
                            entry["colspan"] = cell["colspan"]
                        cells.append(entry)
                rendered["rows"].append(cells)
        rendered_blocks.append(rendered)
    result["blocks"] = rendered_blocks
    if document.provenance:
        result["provenance"] = []
        for item in document.provenance:
            entry: dict[str, Any] = {"block": item.block, "page": item.page}
            if item.bbox is not None:
                entry["bbox"] = list(item.bbox)
            if item.confidence is not None:
                entry["confidence"] = item.confidence
            if item.warnings:
                entry["warnings"] = list(item.warnings)
            if item.evidence is not None:
                entry["evidence"] = item.evidence
            result["provenance"].append(entry)
    return result
