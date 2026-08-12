import json
from pathlib import Path

import pytest

from pdf_to_carve.model import Document, DocumentError, document_to_json

FIXTURE = Path(__file__).parent / "fixtures" / "document.json"


def test_document_round_trips_public_json() -> None:
    raw = json.loads(FIXTURE.read_text())
    assert document_to_json(Document.from_json(raw)) == raw


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"version": 2, "blocks": []}, "version must be 1"),
        ({"version": 1, "blocks": {}, "extra": 1}, "unknown field"),
        ({"version": 1, "blocks": [{"type": "heading", "level": 7, "content": []}]}, "level"),
        (
            {"version": 1, "blocks": [{"type": "paragraph", "content": [{"type": "wat"}]}]},
            "not supported",
        ),
        (
            {"version": 1, "blocks": [{"type": "table", "headers": [[]], "rows": [[[], []]]}]},
            "does not fit",
        ),
        (
            {"version": 1, "blocks": [{"type": "table", "headers": [[], []], "rows": [[[]]]}]},
            "leaves 1 grid",
        ),
        (
            {
                "version": 1,
                "blocks": [
                    {
                        "type": "list",
                        "items": [
                            {"content": []},
                            {"content": [], "checked": True},
                        ],
                    }
                ],
            },
            "must not mix",
        ),
        (
            {
                "version": 1,
                "blocks": [{"type": "admonition", "kind": "not valid", "content": []}],
            },
            "portable name",
        ),
    ],
)
def test_invalid_documents_fail_closed(raw: object, message: str) -> None:
    with pytest.raises(DocumentError, match=message):
        Document.from_json(raw)


def test_spanning_table_round_trips_public_json() -> None:
    raw = {
        "version": 1,
        "blocks": [
            {
                "type": "table",
                "headers": [[], [], [], []],
                "rows": [
                    [[], [], [], []],
                    [
                        {"content": [], "rowspan": 2},
                        [],
                        [],
                        [],
                    ],
                    [{"content": [], "colspan": 2}, []],
                ],
            }
        ],
    }
    assert document_to_json(Document.from_json(raw)) == raw


def test_native_semantic_nodes_round_trip_public_json() -> None:
    raw = {
        "version": 1,
        "blocks": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "highlight", "children": [{"type": "text", "text": "key"}]},
                    {"type": "superscript", "children": [{"type": "text", "text": "2"}]},
                    {
                        "type": "substitute",
                        "children": [{"type": "text", "text": "old"}],
                        "replacement": [{"type": "text", "text": "new"}],
                    },
                    {"type": "footnote", "children": [{"type": "text", "text": "note"}]},
                ],
            },
            {
                "type": "admonition",
                "kind": "note",
                "title": [{"type": "text", "text": "Remember"}],
                "content": [{"type": "text", "text": "Read this."}],
            },
        ],
    }
    assert document_to_json(Document.from_json(raw)) == raw
