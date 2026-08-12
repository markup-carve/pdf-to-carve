from pathlib import Path

import pymupdf
import pytest

from pdf_to_carve.extract import extract_text_pdf, text_coverage
from pdf_to_carve.model import Document
from pdf_to_carve.pipeline import ConversionOptions, convert


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    doc.set_metadata({"title": "Fixture", "author": "Tests"})
    page = doc.new_page()
    page.insert_text((72, 72), "A Large Heading", fontsize=24)
    page.insert_text((72, 120), "This is searchable body text in a normal font.", fontsize=11)
    doc.save(path)
    doc.close()
    return path


def test_extracts_searchable_pdf(text_pdf: Path) -> None:
    raw = extract_text_pdf(text_pdf)
    document = Document.from_json(raw)
    assert document.title == "Fixture"
    assert document.author == "Tests"
    assert [block.type for block in document.blocks] == ["heading", "paragraph"]
    assert text_coverage(text_pdf) > 20


def test_pipeline_auto_selects_text_without_api(text_pdf: Path) -> None:
    result = convert(text_pdf, ConversionOptions(text_threshold=20))
    assert result.mode == "text"
    assert "# A Large Heading" in result.source
    assert "searchable body text" in result.source


def test_bad_page_range_is_rejected(text_pdf: Path) -> None:
    with pytest.raises(ValueError, match="invalid page range"):
        extract_text_pdf(text_pdf, start=2)
