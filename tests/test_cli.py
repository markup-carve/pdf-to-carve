import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf_to_carve.cli import main
from pdf_to_carve.model import Document


def test_from_json_writes_source_and_replayable_json(tmp_path: Path) -> None:
    source = Path(__file__).parent / "fixtures" / "document.json"
    output = tmp_path / "output.crv"
    saved = tmp_path / "saved.json"
    assert main([str(source), "--from-json", "-o", str(output), "--save-json", str(saved)]) == 0
    assert output.read_text().startswith("---yaml")
    assert json.loads(saved.read_text()) == json.loads(source.read_text())


def test_cli_reports_invalid_input(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.json"
    assert main([str(missing), "--from-json"]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_can_emit_annotations_and_run_correction_loop(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps(
            {
                "version": 1,
                "blocks": [{"type": "paragraph", "content": [{"type": "text", "text": "Review"}]}],
                "provenance": [{"block": 0, "page": 1, "confidence": 0.5}],
            }
        )
    )
    output = tmp_path / "output.crv"
    saved = tmp_path / "corrected.json"
    monkeypatch.setattr(
        "sys.stdin",
        __import__("io").StringIO(
            '{"type":"paragraph","content":[{"type":"text","text":"Corrected"}]}\n'
        ),
    )
    assert (
        main(
            [
                str(source),
                "--from-json",
                "--correct",
                "--annotate-confidence",
                "--save-json",
                str(saved),
                "-o",
                str(output),
            ]
        )
        == 0
    )
    assert "original-confidence=0.500 corrected" in output.read_text()
    assert "Corrected" in output.read_text()
    assert json.loads(saved.read_text())["blocks"][0]["content"][0]["text"] == "Corrected"


def test_cli_rejects_confidence_threshold_outside_unit_interval() -> None:
    with pytest.raises(SystemExit, match="2"):
        main(["input.json", "--confidence-threshold", "5"])


def test_cli_writes_correction_workspace_with_source_pdf(tmp_path: Path) -> None:
    source = Path(__file__).parent / "fixtures" / "document.json"
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    workspace = tmp_path / "correction.html"
    assert (
        main(
            [
                str(source),
                "--from-json",
                "--correction-html",
                str(workspace),
                "--source-pdf",
                str(pdf),
            ]
        )
        == 0
    )
    assert "pdf-to-carve correction workspace" in workspace.read_text()


def test_cli_uses_pdf_input_as_default_workspace_preview(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    workspace = tmp_path / "correction.html"
    document = Document.from_json({"version": 1, "blocks": [{"type": "paragraph", "content": []}]})
    monkeypatch.setattr(
        "pdf_to_carve.cli.convert",
        lambda *_args, **_kwargs: SimpleNamespace(
            source="", document=document, mode="text", diagnostics=(), warnings=()
        ),
    )

    assert main([str(pdf), "--correction-html", str(workspace)]) == 0
    assert pdf.resolve().as_uri() in workspace.read_text()


def test_cli_rejects_source_pdf_without_workspace(tmp_path: Path, capsys) -> None:
    source = Path(__file__).parent / "fixtures" / "document.json"
    assert main([str(source), "--from-json", "--source-pdf", "source.pdf"]) == 1
    assert "--source-pdf requires --correction-html" in capsys.readouterr().err
