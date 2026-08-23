from pathlib import Path

import pytest

from pdf_to_carve.pipeline import ConversionOptions, convert

CORPUS = Path(__file__).parent / "pdf_corpus"


@pytest.mark.parametrize(
    "name",
    [
        "assets",
        "columns",
        "furniture",
        "links-footnotes",
        "rotated-code-table",
        "three-columns",
    ],
)
def test_hand_checked_pdf_corpus(name: str, tmp_path: Path) -> None:
    assets = tmp_path / "assets" if name == "assets" else None
    result = convert(CORPUS / f"{name}.pdf", ConversionOptions(mode="text", assets_dir=assets))
    expected = (CORPUS / "expected" / f"{name}.crv").read_text(encoding="utf-8")
    assert result.source == expected
    if name == "assets":
        assert [path.name for path in (tmp_path / "assets").iterdir()] == ["page-1-raster-1.png"]


def test_corpus_surfaces_reviewable_inference_diagnostics(tmp_path: Path) -> None:
    columns = convert(CORPUS / "columns.pdf", ConversionOptions(mode="text"))
    assert columns.warnings == ("page 1: 2-column reading order inferred from stable gutters",)

    assets = convert(
        CORPUS / "assets.pdf",
        ConversionOptions(mode="text", assets_dir=tmp_path / "assets"),
    )
    assert any("placed raster object" in warning for warning in assets.warnings)
