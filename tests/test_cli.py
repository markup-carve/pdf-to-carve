import json
from pathlib import Path

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
