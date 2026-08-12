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
            "must have 1 cells",
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
    ],
)
def test_invalid_documents_fail_closed(raw: object, message: str) -> None:
    with pytest.raises(DocumentError, match=message):
        Document.from_json(raw)
