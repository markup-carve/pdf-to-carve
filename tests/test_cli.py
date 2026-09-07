import json
from pathlib import Path

import pytest

from pdf_to_carve.cli import main


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
