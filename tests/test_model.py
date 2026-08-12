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


def test_provenance_round_trips() -> None:
    raw = {
        "version": 1,
        "blocks": [{"type": "paragraph", "content": []}],
        "provenance": [
            {
                "block": 0,
                "page": 2,
                "bbox": [1, 2.5, 30, 40],
                "confidence": 0.8,
                "warnings": ["check equation"],
                "evidence": "visible text",
            }
        ],
    }
    assert document_to_json(Document.from_json(raw)) == raw


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"block": 1, "page": 1}, "existing block"),
        ({"block": 0, "page": 0}, "positive integer"),
        ({"block": 0, "page": 1, "bbox": [2, 0, 1, 1]}, "ordered coordinates"),
        ({"block": 0, "page": 1, "confidence": 1.1}, "between 0 and 1"),
        ({"block": 0, "page": 1, "warnings": "no"}, "must be an array"),
    ],
)
def test_invalid_provenance_fails_closed(entry: object, message: str) -> None:
    raw = {
        "version": 1,
        "blocks": [{"type": "paragraph", "content": []}],
        "provenance": [entry],
    }
    with pytest.raises(DocumentError, match=message):
        Document.from_json(raw)


def test_duplicate_provenance_fails_closed() -> None:
    raw = {
        "version": 1,
        "blocks": [{"type": "paragraph", "content": []}],
        "provenance": [{"block": 0, "page": 1}, {"block": 0, "page": 2}],
    }
    with pytest.raises(DocumentError, match="at most one"):
        Document.from_json(raw)
