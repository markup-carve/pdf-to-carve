from pathlib import Path

from pdf_to_carve.model import HUMAN_CORRECTED_WARNING, Document
from pdf_to_carve.review import write_review


def test_review_report_escapes_all_untrusted_content(tmp_path: Path) -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}],
            "provenance": [{"block": 0, "page": 1, "warnings": ["uncertain"]}],
        }
    )
    output = tmp_path / "review" / "index.html"
    write_review(output, source="<script>alert(1)</script>", document=document, input_name="<x>")
    rendered = output.read_text()
    assert "<script>alert" not in rendered
    assert "&lt;script&gt;alert" in rendered
    assert "Warnings: 1" in rendered


def test_review_counts_corrections_separately_from_extraction_warnings(tmp_path: Path) -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [{"type": "paragraph", "content": []}],
            "provenance": [{"block": 0, "page": 1, "warnings": [HUMAN_CORRECTED_WARNING]}],
        }
    )
    output = tmp_path / "review.html"
    write_review(output, source="", document=document, input_name="input.pdf")
    rendered = output.read_text()
    assert "Warnings: 0" in rendered
    assert "Corrected blocks: 1" in rendered
