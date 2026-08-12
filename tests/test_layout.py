from pathlib import Path

import pymupdf

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
    assert evidence_prompt(evidence, max_chars=70).endswith("[evidence truncated]")


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
