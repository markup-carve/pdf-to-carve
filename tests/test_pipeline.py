from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest

from pdf_to_carve.model import DocumentError
from pdf_to_carve.pipeline import ConversionOptions, _baseline_prompt, _official_check, convert

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
    assert "TRUSTED TEXT-MODE BASELINE JSON" in transcribe.call_args.kwargs["context"]


def test_hybrid_keeps_deterministic_wording_when_visual_output_changes_it(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    changed = {
        "version": 1,
        "blocks": [{"type": "paragraph", "content": [{"type": "text", "text": "Invented"}]}],
    }
    with patch("pdf_to_carve.pipeline.transcribe_images", return_value=changed):
        result = convert(pdf, ConversionOptions(mode="hybrid", api_key="x"))
    assert "searchable evidence" in result.source
    assert "Invented" not in result.source


def test_hybrid_baseline_prompt_is_bounded_valid_json() -> None:
    document = {
        "version": 1,
        "blocks": [
            {"type": "paragraph", "content": [{"type": "text", "text": "x" * 100}]}
            for _ in range(10)
        ],
    }
    encoded = _baseline_prompt(document, max_chars=250)
    decoded = __import__("json").loads(encoded)
    assert decoded["truncated"] is True
    assert len(encoded) <= 250


def test_hybrid_baseline_prompt_bounds_oversized_metadata_and_marker() -> None:
    document = {
        "version": 1,
        "title": "x" * 1_000,
        "blocks": [
            {"type": "paragraph", "content": [{"type": "text", "text": "y" * 100}]}
            for _ in range(10)
        ],
    }
    encoded = _baseline_prompt(document, max_chars=180)
    assert len(encoded) <= 180
    assert __import__("json").loads(encoded)["truncated"] is True

    metadata_only = _baseline_prompt(
        {"version": 1, "title": "x" * 1_000, "blocks": []}, max_chars=80
    )
    assert __import__("json").loads(metadata_only) == {
        "version": 1,
        "blocks": [],
        "truncated": True,
    }


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


def test_text_mode_returns_an_empty_document_for_a_blank_page(tmp_path: Path) -> None:
    pdf = tmp_path / "blank.pdf"
    document = pymupdf.open()
    document.new_page()
    document.save(pdf)
    document.close()

    result = convert(pdf, ConversionOptions(mode="text"))

    assert result.source == ""
    assert result.document.blocks == ()


def test_auto_routes_an_image_only_pdf_to_vision(tmp_path: Path) -> None:
    pdf = tmp_path / "scan.pdf"
    document = pymupdf.open()
    page = document.new_page(width=200, height=100)
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 100), False)
    pixmap.clear_with(0xFFFFFF)
    page.insert_image(page.rect, pixmap=pixmap)
    document.save(pdf)
    document.close()

    with patch("pdf_to_carve.pipeline.transcribe_images", return_value=EMPTY) as transcribe:
        result = convert(pdf, ConversionOptions(mode="auto", api_key="x"))

    assert result.mode == "vision"
    transcribe.assert_called_once()


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


def test_invalid_library_options_fail_before_extraction(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _pdf(pdf)
    with pytest.raises(ValueError, match="unsupported conversion mode"):
        convert(pdf, ConversionOptions(mode="unknown"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="text_threshold"):
        convert(pdf, ConversionOptions(text_threshold=float("nan")))


def test_invalid_provider_output_is_not_cached(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    cache = tmp_path / "cache"
    _pdf(pdf)
    invalid = {"version": 1, "blocks": [{"type": "unknown"}]}
    with (
        patch("pdf_to_carve.pipeline.transcribe_images", return_value=invalid),
        pytest.raises(DocumentError),
    ):
        convert(pdf, ConversionOptions(mode="vision", api_key="x", cache_dir=cache))
    assert not list(cache.glob("*.json"))


def test_official_check_resolves_a_path_command_and_closes_source_before_running(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "carve"
    executable.write_text("")

    def run(command, **_kwargs):
        assert command[0] == str(executable)
        assert Path(command[-1]).read_text(encoding="utf-8") == "Text\n"
        return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    with (
        patch("pdf_to_carve.pipeline.shutil.which", return_value=str(executable)) as which,
        patch("pdf_to_carve.pipeline.subprocess.run", side_effect=run) as invoked,
    ):
        assert _official_check("Text\n", "carve") == ()
    which.assert_called_once_with("carve")
    assert invoked.call_count == 2
