import json
import re
from pathlib import Path

import pytest

from pdf_to_carve.model import HUMAN_CORRECTED_WARNING, Document
from pdf_to_carve.review import write_correction_workspace, write_review


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


def test_correction_workspace_is_offline_resumable_and_script_safe(tmp_path: Path) -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {"type": "paragraph", "content": [{"type": "text", "text": "</script><x>"}]}
            ],
            "provenance": [{"block": 0, "page": 3, "confidence": 0.42}],
        }
    )
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    output = tmp_path / "workspace" / "index.html"
    write_correction_workspace(output, document=document, input_name="source.pdf", source_pdf=pdf)
    rendered = output.read_text()
    assert "</script><x>" not in rendered
    match = re.search(r'<script id="config" type="application/json">(.*?)</script>', rendered)
    assert match is not None
    config = json.loads(match.group(1))
    assert config["document"]["blocks"][0]["content"][0]["text"] == "</script><x>"
    assert config["pdfUrl"].endswith("source.pdf")
    for contract in (
        "localStorage.getItem",
        "localStorage.setItem",
        "Last accepted change undone",
        "Export corrected JSON",
        "Export regression fixture",
        "#page=${p?.page ?? 1}",
    ):
        assert contract in rendered


def test_correction_workspace_rejects_invalid_source_pdf(tmp_path: Path) -> None:
    document = Document.from_json({"version": 1, "blocks": [{"type": "paragraph", "content": []}]})
    wrong = tmp_path / "source.txt"
    wrong.write_text("not pdf")
    with pytest.raises(ValueError, match="must be a PDF"):
        write_correction_workspace(
            tmp_path / "workspace.html",
            document=document,
            input_name="source.txt",
            source_pdf=wrong,
        )

    fake_pdf = tmp_path / "source.pdf"
    fake_pdf.write_text("not pdf")
    with pytest.raises(ValueError, match="does not have a PDF header"):
        write_correction_workspace(
            tmp_path / "workspace.html",
            document=document,
            input_name="source.pdf",
            source_pdf=fake_pdf,
        )
