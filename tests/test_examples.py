import json
from pathlib import Path

import pymupdf
import pytest

from pdf_to_carve.model import Document, document_to_json
from pdf_to_carve.serialize import to_carve

EXAMPLES = Path(__file__).parents[1] / "examples"
CASES = ("scientific-paper", "financial-report", "editorial-review")


@pytest.mark.parametrize("name", CASES)
def test_example_artifacts_are_valid_and_synchronized(name: str) -> None:
    directory = EXAMPLES / name
    raw = json.loads((directory / "extraction.json").read_text(encoding="utf-8"))
    document = Document.from_json(raw)
    assert document_to_json(document) == raw
    assert to_carve(document) == (directory / "result.crv").read_text(encoding="utf-8")
    assert (directory / "result.md").read_text(encoding="utf-8").strip()
    assert (directory / "README.md").read_text(encoding="utf-8").strip()

    pdf = pymupdf.open(directory / "input.pdf")
    try:
        assert pdf.page_count >= 1
        assert pdf[0].get_text().strip()
    finally:
        pdf.close()
