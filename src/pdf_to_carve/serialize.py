"""Deterministic writer from the extraction model to conservative Carve."""

from __future__ import annotations

import re

from .model import Block, Document, Inline

_SPECIAL = re.compile(r"([\\/*_~=\[\]{}<>`])")
_BLOCK_START = re.compile(r"^(?:#{1,6} |[-+>:] |\||:::)")
_ORDERED_BLOCK_START = re.compile(r"^([A-Za-z0-9]+)([.)]) ")


def _escape(text: str) -> str:
    escaped = _SPECIAL.sub(r"\\\1", text).replace("\r", "").replace("\n", " ")
    return escaped.replace("%%", r"\%%")


def _escape_alt(text: str) -> str:
    return (
        text.replace("\r", "")
        .replace("\n", " ")
        .replace("\\", r"\\")
        .replace("[", r"\[")
        .replace("]", r"\]")
    )


def _escape_block_start(text: str) -> str:
    """Keep literal paragraph text from opening a Carve block."""
    if _BLOCK_START.match(text):
        return f"\\{text}"
    if text == ":::" or re.fullmatch(r"-{3,}", text):
        return f"\\{text}"
    return _ORDERED_BLOCK_START.sub(r"\1\\\2 ", text, count=1)


def _inline(nodes: tuple[Inline, ...], *, table: bool = False) -> str:
    out = []
    previous_text_ends_percent = False
    for node in nodes:
        if node.type == "text":
            value = _escape(node.text)
            if previous_text_ends_percent and node.text.startswith("%"):
                value = "\\" + value
            if table:
                value = value.replace("|", r"\|")
        elif node.type == "code":
            value = _code_span(node.text)
        elif node.type == "math":
            value = f"${_code_span(node.text)}"
        elif node.type == "link":
            url = node.url.replace("\\", "%5C").replace(")", "%29") if node.url else ""
            value = f"[{_inline(node.children, table=table)}]({url})"
        elif node.type == "substitute":
            value = (
                f"{{~{_inline(node.children, table=table)}"
                f"~>{_inline(node.replacement, table=table)}~}}"
            )
        elif node.type == "footnote":
            value = f"^[{_inline(node.children, table=table)}]"
        else:
            marks = {
                "strong": ("*", "*"),
                "emphasis": ("/", "/"),
                "underline": ("_", "_"),
                "strike": ("~", "~"),
                "highlight": ("=", "="),
                "superscript": ("{^", "^}"),
                "subscript": ("{,", ",}"),
                "insert": ("{+", "+}"),
                "delete": ("{-", "-}"),
            }
            opening, closing = marks[node.type]
            value = f"{opening}{_inline(node.children, table=table)}{closing}"
        out.append(value)
        previous_text_ends_percent = node.type == "text" and node.text.endswith("%")
    return "".join(out)


def _code_span(text: str) -> str:
    ticks = "`" * (max((len(m.group()) for m in re.finditer(r"`+", text)), default=0) + 1)
    return f"{ticks}{text}{ticks}"


def _table_rows(rows: list[list[dict[str, object]]], width: int) -> list[str]:
    occupied = [0] * width
    rendered_rows = []
    for row in rows:
        active = [remaining > 0 for remaining in occupied]
        cells = ["^" if column else "" for column in active]
        cursor = 0
        for cell in row:
            while active[cursor]:
                cursor += 1
            colspan = int(cell["colspan"])
            rowspan = int(cell["rowspan"])
            cells[cursor] = _inline(cell["content"], table=True)  # type: ignore[arg-type]
            for column in range(cursor, cursor + colspan):
                active[column] = True
                occupied[column] = max(occupied[column], rowspan)
                if column > cursor:
                    cells[column] = "<"
            cursor += colspan
        rendered_rows.append("| " + " | ".join(cells) + " |")
        occupied = [max(0, remaining - 1) for remaining in occupied]
    return rendered_rows


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
        paragraph = _escape_block_start(_inline(d["content"]))
        return f"{{#{d['id']}}}\n{paragraph}" if "id" in d else paragraph
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
        info = d.get("language", "")
        return f"{fence}{info}\n{text}\n{fence}"
    if block.type == "quote":
        lines = "\n".join(
            f"> {line}" if line else ">" for line in _inline(d["content"]).splitlines()
        )
        if "attribution" in d:
            lines += f"\n^ {_inline(d['attribution'])}"
        return lines
    if block.type == "table":
        markers = {"left": "", "right": ">", "center": "~"}
        alignments = d.get("alignments", ("left",) * len(d["headers"]))
        header = "".join(
            f"|={markers[alignment]} {_inline(cell, table=True)} "
            for cell, alignment in zip(d["headers"], alignments, strict=True)
        )
        rows = [header + "|"]
        rows.extend(_table_rows(d["rows"], len(d["headers"])))
        if "caption" in d:
            rows.append(f"^ {_inline(d['caption'])}")
        return "\n".join(rows)
    if block.type == "figure":
        alt = _escape_alt(d["alt"])
        src = d["src"].replace(")", "%29")
        result = f"![{alt}]({src})"
        if "id" in d:
            result += f" {{#{d['id']}}}"
        if "caption" in d:
            result += f"\n^ {_inline(d['caption'])}"
        return result
    if block.type == "admonition":
        title = f"*{_inline(d['title'])}*\n\n" if "title" in d else ""
        return f"::: {d['kind']}\n{title}{_inline(d['content'])}\n:::"
    if block.type == "thematic_break":
        return "---"
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
    return "\n\n".join(sections).rstrip() + "\n" if sections else ""
