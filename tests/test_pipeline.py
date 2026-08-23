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


def test_hybrid_supplies_pdf_link_destinations_as_evidence(tmp_path: Path) -> None:
    pdf = tmp_path / "linked.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((20, 30), "linked evidence")
    page.insert_link(
        {
            "kind": pymupdf.LINK_URI,
            "from": pymupdf.Rect(20, 18, 100, 34),
            "uri": "https://example.com/docs",
        }
    )
    document.save(pdf)
    document.close()

    options = ConversionOptions(mode="hybrid", api_key="x")
    with patch("pdf_to_carve.pipeline.transcribe_images", return_value=EMPTY) as transcribe:
        convert(pdf, options)
    context = transcribe.call_args.kwargs["context"]
    assert 'URLs=["https://example.com/docs"]' in context


def test_hybrid_can_use_codex_cli_provider(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    options = ConversionOptions(mode="hybrid", provider="codex-cli", model="cli-model")
    with patch("pdf_to_carve.pipeline.transcribe_images_codex", return_value=EMPTY) as transcribe:
        result = convert(pdf, options)
    assert result.mode == "hybrid"
    assert transcribe.call_args.kwargs["model"] == "cli-model"


def test_hybrid_can_use_claude_cli_provider_with_provider_default_model(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    options = ConversionOptions(mode="hybrid", provider="claude-cli")
    with patch("pdf_to_carve.pipeline.transcribe_images_claude", return_value=EMPTY) as transcribe:
        result = convert(pdf, options)
    assert result.mode == "hybrid"
    assert transcribe.call_args.kwargs["model"] == "sonnet"


def test_pymupdf_remains_an_explicit_compatibility_backend(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    result = convert(pdf, ConversionOptions(mode="text", pdf_backend="pymupdf"))
    assert result.mode == "text"
    assert "searchable evidence" in result.source


def test_unknown_pdf_backend_fails_closed(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    with pytest.raises(ValueError, match="unsupported PDF backend"):
        convert(pdf, ConversionOptions(mode="text", pdf_backend="unknown"))  # type: ignore[arg-type]


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
