"""Deterministic writer from the extraction model to conservative Carve."""

from __future__ import annotations

import re

from .model import Block, Document, Inline

_SPECIAL = re.compile(r"([\\/*_~=\[\]{}<>`%])")


def _escape(text: str) -> str:
    return _SPECIAL.sub(r"\\\1", text).replace("\r", "").replace("\n", " ")


def _inline(nodes: tuple[Inline, ...], *, table: bool = False) -> str:
    out = []
    for node in nodes:
        if node.type == "text":
            value = _escape(node.text)
            if table:
                value = value.replace("|", r"\|")
        elif node.type == "code":
            ticks = "`" * (
                max((len(m.group()) for m in re.finditer(r"`+", node.text)), default=0) + 1
            )
            value = f"{ticks}{node.text}{ticks}"
        elif node.type == "math":
            math = node.text.replace("$", r"\$")
            value = f"${math}$"
        elif node.type == "link":
            url = node.url.replace("\\", "%5C").replace(")", "%29") if node.url else ""
            value = f"[{_inline(node.children)}]({url})"
        else:
            marks = {"strong": "*", "emphasis": "/", "underline": "_", "strike": "~"}
            mark = marks[node.type]
            value = f"{mark}{_inline(node.children)}{mark}"
        out.append(value)
    return "".join(out)


def _frontmatter(doc: Document) -> str:
    values = [("title", doc.title), ("author", doc.author), ("lang", doc.language)]
    present = [(key, value) for key, value in values if value is not None]
    if not present:
        return ""
    lines = ["---yaml"]
    for key, value in present:
        assert value is not None
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines)


def _block(block: Block) -> str:
    d = block.data
    if block.type == "heading":
        heading = f"{'#' * d['level']} {_inline(d['content'])}"
        return f"{{#{d['id']}}}\n{heading}" if "id" in d else heading
    if block.type == "paragraph":
        return _inline(d["content"])
    if block.type == "list":
        lines = []
        for index, item in enumerate(d["items"]):
            marker = f"{d['start'] + index}." if d["ordered"] else "-"
            task = f" [{'x' if item['checked'] else ' '}]" if "checked" in item else ""
            lines.append(f"{marker}{task} {_inline(item['content'])}")
        return "\n".join(lines)
    if block.type == "code_block":
        text = d["text"].rstrip("\n")
        longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
        fence = "`" * max(3, longest + 1)
        return f"{fence}{d.get('language', '')}\n{text}\n{fence}"
    if block.type == "quote":
        lines = "\n".join(
            f"> {line}" if line else ">" for line in _inline(d["content"]).splitlines()
        )
        if "attribution" in d:
            lines += f"\n^ {_inline(d['attribution'])}"
        return lines
    if block.type == "table":
        rows = ["|=" + "|=".join(_inline(cell, table=True) for cell in d["headers"]) + "|"]
        rows.extend(
            "| " + " | ".join(_inline(cell, table=True) for cell in row) + " |" for row in d["rows"]
        )
        if "caption" in d:
            rows.append(f"^ {_inline(d['caption'])}")
        return "\n".join(rows)
    if block.type == "figure":
        alt = _escape(d["alt"]).replace("]", r"\]")
        src = d["src"].replace(")", "%29")
        result = f"![{alt}]({src})"
        if "id" in d:
            result += f" {{#{d['id']}}}"
        if "caption" in d:
            result += f"\n^ {_inline(d['caption'])}"
        return result
    if block.type == "thematic_break":
        return "***"
    if block.type == "page_break":
        return "::: page-break\n\n:::"
    raise AssertionError(f"unhandled block type: {block.type}")


def to_carve(document: Document) -> str:
    """Serialize a validated document to stable Carve source."""
    sections = []
    frontmatter = _frontmatter(document)
    if frontmatter:
        sections.append(frontmatter)
    sections.extend(rendered for block in document.blocks if (rendered := _block(block)))
    return "\n\n".join(sections).rstrip() + "\n"
