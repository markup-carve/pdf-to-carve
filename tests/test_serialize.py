import json
from pathlib import Path

from pdf_to_carve.model import Document
from pdf_to_carve.serialize import to_carve

FIXTURE = Path(__file__).parent / "fixtures" / "document.json"


def test_serializes_native_carve_without_markdown_stage() -> None:
    source = to_carve(Document.from_json(json.loads(FIXTURE.read_text())))
    assert source.startswith('---yaml\ntitle: "Example Document"')
    assert "{#results}\n# Results & discussion" in source
    assert "The *important* result is $x^2$." in source
    assert "|=Name|=Value|" in source
    assert "`a|b`" in source
    assert "- [ ] first" in source
    assert "- [x] done" in source
    assert "![Architecture](assets/page-1-figure-1.png) {#architecture}" in source


def test_escapes_document_text_and_variable_code_fences() -> None:
    raw = {
        "version": 1,
        "blocks": [
            {"type": "paragraph", "content": [{"type": "text", "text": "literal * / _ ~ [ %"}]},
            {"type": "code_block", "language": "txt", "text": "contains ``` inside"},
        ],
    }
    source = to_carve(Document.from_json(raw))
    assert r"literal \* \/ \_ \~ \[ \%" in source
    assert "````txt\ncontains ``` inside\n````" in source


def test_page_break_uses_canonical_nonempty_container_layout() -> None:
    source = to_carve(Document.from_json({"version": 1, "blocks": [{"type": "page_break"}]}))
    assert source == "::: page-break\n\n:::\n"
