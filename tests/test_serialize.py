import json
from pathlib import Path

from pdf_to_carve.model import Document
from pdf_to_carve.serialize import to_carve

FIXTURE = Path(__file__).parent / "fixtures" / "document.json"


def test_serializes_native_carve_without_markdown_stage() -> None:
    source = to_carve(Document.from_json(json.loads(FIXTURE.read_text())))
    assert source.startswith('---yaml\ntitle: "Example Document"')
    assert "{#results}\n# Results & discussion" in source
    assert "The *important* result is $`x^2`." in source
    assert "|= Name |= Value |" in source
    assert "`a|b`" in source
    assert "- [ ] first" in source
    assert "- [x] done" in source
    assert "![Architecture](assets/page-1-figure-1.png){#architecture}" in source


def test_escapes_document_text_and_variable_code_fences() -> None:
    raw = {
        "version": 1,
        "blocks": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "literal * / _ ~ [ 13.7% %% note"}],
            },
            {"type": "code_block", "language": "txt", "text": "contains ``` inside"},
        ],
    }
    source = to_carve(Document.from_json(raw))
    assert r"literal \* \/ \_ \~ \[ 13.7% \%% note" in source
    assert "````txt\ncontains ``` inside\n````" in source


def test_escapes_literal_block_openers_in_paragraphs() -> None:
    values = [
        "# not a heading",
        "### not a heading",
        "- not a list item",
        "+ not a list item",
        "> not a quote",
        "1. not an ordered item",
        "a) not an ordered item",
        "::: not a container",
        "| not a table",
        "---",
    ]
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {"type": "paragraph", "content": [{"type": "text", "text": value}]}
                for value in values
            ],
        }
    )
    assert to_carve(document) == (
        "\\# not a heading\n\n"
        "\\### not a heading\n\n"
        "\\- not a list item\n\n"
        "\\+ not a list item\n\n"
        "\\> not a quote\n\n"
        "1\\. not an ordered item\n\n"
        "a\\) not an ordered item\n\n"
        "\\::: not a container\n\n"
        "\\| not a table\n\n"
        "\\---\n"
    )


def test_escapes_comment_marker_split_across_text_nodes() -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Shown: "},
                        {"type": "text", "text": "%"},
                        {"type": "text", "text": "% hidden"},
                    ],
                }
            ],
        }
    )
    assert to_carve(document) == "Shown: %\\% hidden\n"


def test_page_break_uses_canonical_nonempty_container_layout() -> None:
    source = to_carve(Document.from_json({"version": 1, "blocks": [{"type": "page_break"}]}))
    assert source == "::: page-break\n\n:::\n"


def test_math_and_thematic_break_use_native_carve_syntax() -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {"type": "paragraph", "content": [{"type": "math", "text": "x^2"}]},
                {"type": "thematic_break"},
            ],
        }
    )
    assert to_carve(document) == "$`x^2`\n\n---\n"


def test_figure_alt_keeps_plain_underscores_and_escapes_brackets() -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [{"type": "figure", "src": "image.png", "alt": "print_cdp.py [diagram]"}],
        }
    )
    assert to_carve(document) == r"![print_cdp.py \[diagram\]](image.png)" + "\n"


def test_table_spans_emit_native_carve_placeholders() -> None:
    def cell(text: str) -> list[dict[str, str]]:
        return [{"type": "text", "text": text}]

    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {
                    "type": "table",
                    "headers": [cell("Region"), cell("Q1"), cell("Q2"), cell("Q3")],
                    "alignments": ["left", "right", "center", "left"],
                    "rows": [
                        [cell("EMEA"), cell("12"), cell("15"), cell("19")],
                        [
                            {"content": cell("APAC"), "rowspan": 2},
                            cell("8"),
                            cell("11"),
                            cell("22"),
                        ],
                        [{"content": cell("20"), "colspan": 2}, cell("25")],
                    ],
                }
            ],
        }
    )
    assert to_carve(document) == (
        "|= Region |=> Q1 |=~ Q2 |= Q3 |\n"
        "| EMEA | 12 | 15 | 19 |\n"
        "| APAC | 8 | 11 | 22 |\n"
        "| ^ | 20 | < | 25 |\n"
    )


def test_serializes_native_semantic_nodes() -> None:
    def text(value: str) -> list[dict[str, str]]:
        return [{"type": "text", "text": value}]

    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "highlight", "children": text("key")},
                        {"type": "superscript", "children": text("2")},
                        {"type": "subscript", "children": text("n")},
                        {"type": "insert", "children": text("add")},
                        {"type": "delete", "children": text("drop")},
                        {"type": "substitute", "children": text("old"), "replacement": text("new")},
                        {"type": "footnote", "children": text("note")},
                    ],
                },
                {
                    "type": "admonition",
                    "kind": "note",
                    "title": text("Remember"),
                    "content": text("Read this."),
                },
            ],
        }
    )
    assert to_carve(document) == (
        "=key={^2^}{,n,}{+add+}{-drop-}{~old~>new~}^[note]\n\n"
        "::: note\n*Remember*\n\nRead this.\n:::\n"
    )


def test_paragraph_id_emits_a_block_attribute_anchor() -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {
                    "type": "paragraph",
                    "id": "page-2",
                    "content": [{"type": "text", "text": "Destination"}],
                }
            ],
        }
    )
    assert to_carve(document) == "{#page-2}\nDestination\n"


def test_table_escapes_pipes_inside_nested_inline_nodes() -> None:
    text = [{"type": "text", "text": "a|b"}]
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {
                    "type": "table",
                    "headers": [text],
                    "rows": [[[{"type": "strong", "children": text}]]],
                }
            ],
        }
    )
    assert to_carve(document) == "|= a\\|b |\n| *a\\|b* |\n"
