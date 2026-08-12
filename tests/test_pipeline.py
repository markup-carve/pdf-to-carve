from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest

from pdf_to_carve.pipeline import ConversionOptions, convert

EMPTY = {"version": 1, "blocks": []}


def _pdf(path: Path, pages: int = 1) -> None:
    doc = pymupdf.open()
    for number in range(pages):
        page = doc.new_page()
        page.insert_text((20, 30), f"Page {number + 1} searchable evidence")
    doc.save(path)
    doc.close()


def test_hybrid_supplies_positioned_text_and_reuses_cache(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    options = ConversionOptions(mode="hybrid", api_key="x", cache_dir=tmp_path / "cache")
    with patch("pdf_to_carve.pipeline.transcribe_images", return_value=EMPTY) as transcribe:
        first = convert(pdf, options)
        second = convert(pdf, options)
    assert first.mode == second.mode == "hybrid"
    assert transcribe.call_count == 1
    assert "searchable evidence" in transcribe.call_args.kwargs["context"]


def test_vision_page_limit_is_enforced_before_request(tmp_path: Path) -> None:
    pdf = tmp_path / "long.pdf"
    _pdf(pdf, pages=2)
    with pytest.raises(ValueError, match="maximum is 1"):
        convert(pdf, ConversionOptions(mode="vision", max_pages=1, api_key="x"))


@pytest.mark.parametrize("dpi", [71, 401])
def test_vision_dpi_is_bounded(tmp_path: Path, dpi: int) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    with pytest.raises(ValueError, match="dpi"):
        convert(pdf, ConversionOptions(mode="vision", dpi=dpi, api_key="x"))


def test_hybrid_rejects_image_input(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    with pytest.raises(ValueError, match="PDF input only"):
        convert(image, ConversionOptions(mode="hybrid", api_key="x"))


def test_input_size_limit_is_enforced(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="1 MiB"):
        convert(image, ConversionOptions(mode="vision", max_input_mb=1, api_key="x"))
