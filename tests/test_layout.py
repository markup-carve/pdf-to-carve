from pathlib import Path

import pymupdf
import pytest

from pdf_to_carve.layout import evidence_prompt, extract_embedded_images, positioned_text


def _pdf(path: Path, *, image: Path | None = None) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.insert_text((20, 30), "Positioned text")
    if image:
        page.insert_image(pymupdf.Rect(20, 50, 40, 70), filename=image)
        page.insert_image(pymupdf.Rect(50, 50, 70, 70), filename=image)
    doc.save(path)
    doc.close()


def test_positioned_text_and_bounded_evidence(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    _pdf(path)
    evidence = positioned_text(path)
    assert evidence[0]["page"] == 1
    assert evidence[0]["text"] == "Positioned text"
    assert len(evidence[0]["bbox"]) == 4
    assert "untrusted data" in evidence_prompt(evidence)
    assert evidence_prompt(evidence, max_bytes=100).endswith("[evidence truncated]")


def test_evidence_prompt_budget_counts_utf8_bytes() -> None:
    evidence = [{"page": 1, "bbox": [0, 0, 1, 1], "text": "é" * 20}]
    prompt = evidence_prompt(evidence, max_bytes=100)

    assert prompt.endswith("[evidence truncated]")
    assert len(prompt.encode("utf-8")) <= 100


def test_evidence_prompt_rejects_budget_smaller_than_header() -> None:
    with pytest.raises(ValueError, match="budget is too small"):
        evidence_prompt([], max_bytes=10)


def test_evidence_prompt_rejects_budget_that_cannot_report_truncation() -> None:
    evidence = [{"page": 1, "bbox": [0, 0, 1, 1], "text": "too large"}]
    with pytest.raises(ValueError, match="cannot fit truncation marker"):
        evidence_prompt(evidence, max_bytes=80)


def test_positioned_text_rejects_invalid_range(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    _pdf(path)
    try:
        positioned_text(path, start=2)
    except ValueError as exc:
        assert "invalid page range" in str(exc)
    else:
        raise AssertionError("invalid range accepted")


def test_embedded_images_are_deduplicated(tmp_path: Path) -> None:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), False)
    pix.clear_with(0x336699)
    image = tmp_path / "source.png"
    pix.save(image)
    pdf = tmp_path / "image.pdf"
    _pdf(pdf, image=image)
    assets = extract_embedded_images(pdf, tmp_path / "assets")
    assert len(assets) == 1
    assert assets[0].is_file()
    assert assets[0].name.startswith("page-1-figure-1.")


def test_embedded_images_honor_page_range(tmp_path: Path) -> None:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), False)
    pix.clear_with(0x336699)
    image = tmp_path / "source.png"
    pix.save(image)
    pdf = tmp_path / "pages.pdf"
    document = pymupdf.open()
    for _ in range(2):
        page = document.new_page(width=100, height=100)
        page.insert_image(pymupdf.Rect(10, 10, 30, 30), filename=image)
    document.save(pdf)
    document.close()

    assets = extract_embedded_images(pdf, tmp_path / "assets", start=2, end=2)

    assert [asset.name for asset in assets] == ["page-2-figure-1.png"]
