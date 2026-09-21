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
    assert calculated == json.loads((directory / "results.json").read_text(encoding="utf-8"))
    assert scorer.report(calculated) == (directory / "REPORT.md").read_text(encoding="utf-8")


def test_failed_or_missing_outputs_are_not_scored_as_zero() -> None:
    tools = {tool["id"]: tool for tool in _scorer().calculate()["tools"]}
    assert tools["markpdfdown"]["completed"] == 0
    assert "mean_character" not in tools["markpdfdown"]
    assert tools["docling"]["completed"] == 1


def test_ground_truth_uses_the_current_substitution_shape() -> None:
    # `substitution` carried the strings `oldText` and `newText` until
    # markup-carve/carve-js#1827 replaced them with `old` and `new`, two arrays
    # of inline nodes. Both keys are required and an empty half is `[]`.
    truth = Path(__file__).parents[1] / "benchmarks" / "competitors" / "raw" / "truth"
    found = 0
    for path in sorted(truth.glob("*.ast.json")):
        for node in _nodes(json.loads(path.read_text(encoding="utf-8"))):
            if node.get("type") != "substitution":
                continue
            found += 1
            assert isinstance(node.get("old"), list), f"{path.name}: substitution has no old array"
            assert isinstance(node.get("new"), list), f"{path.name}: substitution has no new array"
            retired = {"oldText", "newText"} & set(node)
            assert not retired, f"{path.name}: retired field names {sorted(retired)}"
    assert found == 1, f"expected one substitution in the ground truth, found {found}"


def test_carve_asts_record_the_source_beside_them() -> None:
    # Catches a source rewritten without its AST, unless the byte length held.
    raw = Path(__file__).parents[1] / "benchmarks" / "competitors" / "raw"
    checked = 0
    for source in sorted(raw.glob("carve-*/*.source.crv")):
        ast = source.with_name(source.name.replace(".source.crv", ".ast.json"))
        recorded = json.loads(ast.read_text(encoding="utf-8"))["srcByteLength"]
        assert recorded == len(source.read_bytes()), f"{ast.relative_to(raw)} is stale"
        checked += 1
    assert checked == 8, f"expected eight carve-* sources, found {checked}"


def _nodes(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nodes(child)
