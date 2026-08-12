import importlib.util
import json
from pathlib import Path


def _scorer():
    path = Path(__file__).parents[1] / "benchmarks" / "competitors" / "score.py"
    spec = importlib.util.spec_from_file_location("competitor_score", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_competitor_benchmark_artifacts_are_reproducible() -> None:
    scorer = _scorer()
    calculated = scorer.calculate()
    directory = Path(__file__).parents[1] / "benchmarks" / "competitors"
    assert calculated == json.loads((directory / "results.json").read_text())
    assert scorer.report(calculated) == (directory / "REPORT.md").read_text()


def test_failed_or_missing_outputs_are_not_scored_as_zero() -> None:
    tools = {tool["id"]: tool for tool in _scorer().calculate()["tools"]}
    assert tools["markpdfdown"]["completed"] == 0
    assert "mean_character" not in tools["markpdfdown"]
    assert tools["docling"]["completed"] == 1
