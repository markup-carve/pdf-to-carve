from pathlib import Path

from pdf_to_carve.model import Document
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
