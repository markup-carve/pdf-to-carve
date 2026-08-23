"""What the writer emits, read back by a Carve engine.

Every other test here asserts on the Carve SOURCE the writer produces - that a
figure line holds `{#id}`, that a table header holds `|=`. Valid source is not
the same claim as correct source: `![a](b) {#fig-1}` and `![a](b){#fig-1}` are
both well-formed Carve that `carve fmt` and `carve lint` accept, and only one of
them is a figure with an id. The other renders an image, a `#fig-1` tag and a
stray caption line inside one paragraph, which is how that spelling survived
release (markup-carve/pdf-to-carve#15).

So this file renders each construct with `carve-lang`, the PyO3 binding over
carve-rs, and asserts the HTML says what the extraction model meant. A pinned
engine is what makes the answers reproducible; a gate that runs it is what makes
the pin worth having.

WHY A CONSTRUCT TABLE AND NOT THE CORPUS. The writer's input space is
`document-v1.schema.json`, and the example documents and the PDF corpus cover a
slice of it - not one of the ten committed `.crv` answer keys carries a figure
with an id, so rendering all of them finds nothing. The rows below are keyed by
schema type instead, and `test_every_schema_type_is_covered` fails when a type
is added without one.
"""

import json
from pathlib import Path

import carve
import pytest

from pdf_to_carve.model import Document
from pdf_to_carve.serialize import to_carve

SCHEMA = Path(__file__).parents[1] / "src" / "pdf_to_carve" / "document-v1.schema.json"


def _text(value: str) -> dict[str, object]:
    return {"type": "text", "text": value}


def _render(block: dict[str, object]) -> str:
    return carve.to_html(to_carve(Document.from_json({"version": 1, "blocks": [block]})))


def _render_inline(node: dict[str, object]) -> str:
    return _render({"type": "paragraph", "content": [_text("x "), node, _text(" y")]})


# Keyed by the schema's block type. A row's expectations are the properties the
# extraction model is asserting about the document - an id that addresses
# something, an alignment that reaches the cells, a caption bound to its figure.
BLOCK_CASES: dict[str, tuple[dict[str, object], tuple[str, ...]]] = {
    "heading": (
        {"type": "heading", "level": 2, "id": "sec-1", "content": [_text("Results")]},
        ('<section id="sec-1">', "<h2>Results</h2>"),
    ),
    "paragraph": (
        {"type": "paragraph", "id": "p-1", "content": [_text("Body text.")]},
        ('<p id="p-1">Body text.</p>',),
    ),
    "list": (
        {
            "type": "list",
            "ordered": True,
            "start": 3,
            "items": [{"content": [_text("three")]}, {"content": [_text("four")]}],
        },
        ('<ol start="3">', "<li>three</li>"),
    ),
    "code_block": (
        {"type": "code_block", "language": "python", "text": "x = 1"},
        ('<code class="language-python">',),
    ),
    "quote": (
        {
            "type": "quote",
            "content": [_text("Quoted line")],
            "attribution": [_text("Some Author")],
        },
        ("<blockquote>", "<figcaption>Some Author</figcaption>"),
    ),
    "table": (
        {
            "type": "table",
            "headers": [[_text("Left")], [_text("Right")], [_text("Center")]],
            "alignments": ["left", "right", "center"],
            "rows": [
                [
                    {"content": [_text("a")]},
                    {"content": [_text("b")]},
                    {"content": [_text("c")]},
                ]
            ],
            "caption": [_text("Cap")],
        },
        (
            "<caption>Cap</caption>",
            '<th scope="col" style="text-align: right;">Right</th>',
            '<td style="text-align: center;">c</td>',
        ),
    ),
    "figure": (
        {
            "type": "figure",
            "src": "img.png",
            "alt": "Alt text",
            "id": "fig-1",
            "caption": [_text("Caption")],
        },
        ("<figure>", 'id="fig-1"', "<figcaption>Caption</figcaption>"),
    ),
    "admonition": (
        {
            "type": "admonition",
            "kind": "note",
            "title": [_text("Heads up")],
            "content": [_text("Body")],
        },
        ('class="admonition note"', "<strong>Heads up</strong>"),
    ),
    "thematic_break": ({"type": "thematic_break"}, ("<hr>",)),
    "page_break": ({"type": "page_break"}, ('<div class="page-break">',)),
}

INLINE_CASES: dict[str, tuple[dict[str, object], tuple[str, ...]]] = {
    "text": (_text("plain"), ("<p>x plain y</p>",)),
    "code": ({"type": "code", "text": "a|b"}, ("<code>a|b</code>",)),
    "math": ({"type": "math", "text": "x^2"}, ('class="math inline"', r"\(x^2\)")),
    "strong": ({"type": "strong", "children": [_text("b")]}, ("<strong>b</strong>",)),
    "emphasis": ({"type": "emphasis", "children": [_text("i")]}, ("<em>i</em>",)),
    "underline": ({"type": "underline", "children": [_text("u")]}, ("<u>u</u>",)),
    "strike": ({"type": "strike", "children": [_text("s")]}, ("<s>s</s>",)),
    "highlight": ({"type": "highlight", "children": [_text("h")]}, ("<mark>h</mark>",)),
    "superscript": ({"type": "superscript", "children": [_text("2")]}, ("<sup>2</sup>",)),
    "subscript": ({"type": "subscript", "children": [_text("n")]}, ("<sub>n</sub>",)),
    "insert": ({"type": "insert", "children": [_text("new")]}, ("<ins>new</ins>",)),
    "delete": ({"type": "delete", "children": [_text("old")]}, ("<del>old</del>",)),
    "footnote": (
        {"type": "footnote", "children": [_text("a note")]},
        ('role="doc-noteref"', "a note"),
    ),
    "substitute": (
        {"type": "substitute", "children": [_text("old")], "replacement": [_text("new")]},
        ("<del>old</del><ins>new</ins>",),
    ),
    "link": (
        {"type": "link", "url": "https://example.com/a", "children": [_text("site")]},
        ('<a href="https://example.com/a">site</a>',),
    ),
}


@pytest.mark.parametrize("name", sorted(BLOCK_CASES))
def test_block_renders_what_the_model_means(name: str) -> None:
    block, expected = BLOCK_CASES[name]
    html = _render(block)
    for fragment in expected:
        assert fragment in html, f"{name}: {fragment!r} missing from {html!r}"


@pytest.mark.parametrize("name", sorted(INLINE_CASES))
def test_inline_renders_what_the_model_means(name: str) -> None:
    node, expected = INLINE_CASES[name]
    html = _render_inline(node)
    for fragment in expected:
        assert fragment in html, f"{name}: {fragment!r} missing from {html!r}"


@pytest.mark.parametrize("name", ["strong", "emphasis", "underline", "strike", "highlight"])
@pytest.mark.parametrize("prefix,suffix", [("a", "b"), ("", ""), ("(", ")")])
@pytest.mark.parametrize("content", ["mid", " leading", "trailing ", " both "])
def test_boundary_sensitive_marks_survive_every_text_boundary(
    name: str, prefix: str, suffix: str, content: str
) -> None:
    """Generated marks must not depend on whitespace or sibling characters."""
    tag = {
        "strong": "strong",
        "emphasis": "em",
        "underline": "u",
        "strike": "s",
        "highlight": "mark",
    }[name]
    html = _render(
        {
            "type": "paragraph",
            "content": [_text(prefix), {"type": name, "children": [_text(content)]}, _text(suffix)],
        }
    )
    marked = content.strip() if name == "underline" and not prefix and not suffix else content
    assert f"<{tag}>{marked}</{tag}>" in html


@pytest.mark.parametrize("name,tag", [("strong", "strong"), ("emphasis", "em")])
def test_redundant_same_type_nesting_is_flattened(name: str, tag: str) -> None:
    html = _render_inline(
        {
            "type": name,
            "children": [_text("a"), {"type": name, "children": [_text("b")]}, _text("c")],
        }
    )
    assert f"<{tag}>abc</{tag}>" in html
    assert html.count(f"<{tag}>") == 1


@pytest.mark.parametrize("name,tag", [("code", "code"), ("math", "span")])
@pytest.mark.parametrize("content", ["`", "``", "`edge", "edge`"])
def test_verbatim_backtick_edges_survive_their_fence(name: str, tag: str, content: str) -> None:
    html = _render_inline({"type": name, "text": content})
    assert f"<{tag}" in html
    assert content in html
    if name == "math":
        assert 'class="math inline"' in html


def _schema_types(definition: str) -> set[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    found: set[str] = set()
    for variant in schema["$defs"][definition]["oneOf"]:
        kind = variant.get("properties", {}).get("type", {})
        if "const" in kind:
            found.add(kind["const"])
        found.update(kind.get("enum", ()))
    return found


def test_every_schema_type_is_covered() -> None:
    """A construct with no row here is a construct nothing reads back.

    The tables above are the whole gate, so a type the writer learns to emit
    without one is invisible to it - which is how a check stops being a check.
    """
    assert _schema_types("block") == set(BLOCK_CASES)
    assert _schema_types("inline") == set(INLINE_CASES)


def test_a_figure_id_binds_to_the_image_and_not_to_the_text() -> None:
    """The regression that opened this file (markup-carve/pdf-to-carve#15).

    A space between `![alt](src)` and `{#id}` detaches the attribute: the braces
    become literal text, `#fig-1` becomes a tag, and the caption line never
    binds. Both spellings pass `carve fmt --check` and `carve lint`, so the
    existing optional CLI verification could not see it.
    """
    html = _render(
        {
            "type": "figure",
            "src": "img.png",
            "alt": "Alt",
            "id": "fig-1",
            "caption": [_text("Caption")],
        }
    )
    assert '<img src="img.png" alt="Alt" id="fig-1">' in html
    assert '<span class="tag">' not in html
    assert "{#" not in html


@pytest.mark.parametrize(
    "url",
    [
        "https://en.wikipedia.org/wiki/Carve_(markup)",
        "https://example.com/a(b",
        "https://example.com/a)b",
    ],
)
def test_a_parenthesis_in_a_url_keeps_the_link(url: str) -> None:
    """Escaping half a balanced pair is worse than escaping neither.

    The destination scan is balanced-paren-aware, so `Carve_(markup)` was
    already a working URL - and encoding only the closing paren produced
    `Carve_(markup%29`, whose `(` is now unbalanced, which drops the link to
    literal text (markup-carve/pdf-to-carve#15).
    """
    html = _render_inline({"type": "link", "url": url, "children": [_text("site")]})
    assert "<a href=" in html
    assert ">site</a>" in html


@pytest.mark.parametrize(
    "path",
    sorted(
        [
            *(Path(__file__).parents[1] / "examples").glob("*/result.crv"),
            *(Path(__file__).parent / "pdf_corpus" / "expected").glob("*.crv"),
        ]
    ),
    ids=lambda path: path.parent.name + "/" + path.name,
)
def test_a_shipped_document_holds_no_detached_attribute(path: Path) -> None:
    """The corpus cannot find an untaken shape, but it can find a taken one.

    A `{` or a `#word` tag surviving into the HTML means an attribute the writer
    meant to attach did not, which is the tell the figure defect left. Weaker
    than the tables above and cheap enough to keep beside them.
    """
    html = carve.to_html(path.read_text(encoding="utf-8"))
    assert '<span class="tag">' not in html
    assert "{#" not in html
