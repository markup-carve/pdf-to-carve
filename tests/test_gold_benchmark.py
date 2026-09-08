import importlib.util
import json
from copy import deepcopy
from pathlib import Path

SCORE = Path(__file__).parents[1] / "benchmarks" / "gold" / "score.py"
SPEC = importlib.util.spec_from_file_location("gold_score", SCORE)
assert SPEC and SPEC.loader
gold_score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gold_score)


def test_edit_counts_names_each_error_class() -> None:
    assert gold_score.edit_counts("abc", "axcd") == {
        "distance": 2,
        "insertions": 1,
        "deletions": 0,
        "substitutions": 1,
    }


def test_published_gold_results_reproduce_exactly() -> None:
    published = json.loads(SCORE.with_name("results.json").read_text(encoding="utf-8"))
    assert gold_score.build_report() == published
    assert gold_score.render_markdown(published) == SCORE.with_name("REPORT.md").read_text(
        encoding="utf-8"
    )
    assert published["overall"]["documents"] == 7


def test_markdown_derives_version_size_labels_and_error_counts() -> None:
    published = json.loads(SCORE.with_name("results.json").read_text(encoding="utf-8"))
    changed = deepcopy(published)
    changed["overall"]["documents"] = 8
    changed["overall"]["character_errors"]["insertions"] = 2
    changed["by_class"]["new-class"] = changed["by_class"]["references"]
    rendered = gold_score.render_markdown(changed)
    assert "Gold set: 8" in rendered
    assert "Character edits: 2 insertions" in rendered
    assert "| new-class |" in rendered
