"""Small, provider-neutral document model and strict JSON validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DocumentError(ValueError):
    """Raised when extracted document JSON does not match the contract."""


INLINE_TYPES = {"text", "strong", "emphasis", "underline", "strike", "code", "math", "link"}
BLOCK_TYPES = {
    "heading",
    "paragraph",
    "list",
    "code_block",
    "quote",
    "table",
    "figure",
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

    @classmethod
    def from_json(cls, value: Any, path: str) -> Inline:
        obj = _object(value, path)
        kind = _string(obj.get("type"), f"{path}.type", empty=False)
        if kind not in INLINE_TYPES:
            raise DocumentError(f"{path}.type is not supported: {kind}")
        if kind in {"text", "code", "math"}:
            _keys(obj, {"type", "text"}, path)
            return cls(kind, text=_string(obj.get("text"), f"{path}.text"))
        if kind == "link":
            _keys(obj, {"type", "children", "url"}, path)
            url = _string(obj.get("url"), f"{path}.url", empty=False)
        else:
            _keys(obj, {"type", "children"}, path)
            url = None
        raw_children = obj.get("children")
        if not isinstance(raw_children, list) or not raw_children:
            raise DocumentError(f"{path}.children must be a non-empty array")
        children = tuple(
            cls.from_json(item, f"{path}.children[{i}]") for i, item in enumerate(raw_children)
        )
        return cls(kind, children=children, url=url)


def _inlines(value: Any, path: str) -> tuple[Inline, ...]:
    if not isinstance(value, list):
        raise DocumentError(f"{path} must be an array")
    return tuple(Inline.from_json(item, f"{path}[{i}]") for i, item in enumerate(value))


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
            _keys(obj, {"type", "headers", "rows", "caption"}, path)
            headers = obj.get("headers")
            rows = obj.get("rows")
            if not isinstance(headers, list) or not headers:
                raise DocumentError(f"{path}.headers must be a non-empty array")
            if not isinstance(rows, list):
                raise DocumentError(f"{path}.rows must be an array")
            parsed_headers = [
                _inlines(cell, f"{path}.headers[{i}]") for i, cell in enumerate(headers)
            ]
            parsed_rows = []
            for y, row in enumerate(rows):
                if not isinstance(row, list) or len(row) != len(headers):
                    raise DocumentError(f"{path}.rows[{y}] must have {len(headers)} cells")
                parsed_rows.append(
                    [_inlines(cell, f"{path}.rows[{y}][{x}]") for x, cell in enumerate(row)]
                )
            data = {"headers": parsed_headers, "rows": parsed_rows}
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
        else:
            _keys(obj, {"type"}, path)
            data = {}
        return cls(kind, data)


@dataclass(frozen=True)
class Document:
    blocks: tuple[Block, ...]
    title: str | None = None
    author: str | None = None
    language: str | None = None

    @classmethod
    def from_json(cls, value: Any) -> Document:
        obj = _object(value, "document")
        _keys(obj, {"version", "title", "author", "language", "blocks"}, "document")
        if obj.get("version") != 1:
            raise DocumentError("document.version must be 1")
        raw_blocks = obj.get("blocks")
        if not isinstance(raw_blocks, list):
            raise DocumentError("document.blocks must be an array")
        metadata = {}
        for name in ("title", "author", "language"):
            if name in obj:
                metadata[name] = _string(obj[name], f"document.{name}", empty=False)
        return cls(
            blocks=tuple(
                Block.from_json(item, f"document.blocks[{i}]") for i, item in enumerate(raw_blocks)
            ),
            **metadata,
        )


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
        rendered_blocks.append(rendered)
    result["blocks"] = rendered_blocks
    return result
