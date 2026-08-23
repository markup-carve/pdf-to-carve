"""Every committed Markdown snapshot still comes from its Carve source.

`examples/README.md` records which engine rendered the snapshots, so that a
later change to them is "attributable and reviewable". Recording a pin is not
the same as checking it: the note stayed put while the snapshots aged two Carve
releases behind it, and by the time anyone looked the export had stopped
escaping a bare percent and had learned to carry a table caption that two
example READMEs still described as lost. A pin nothing re-runs is a claim about
the past.

So this regenerates each `.md` from its `.crv` with the pinned engine and
compares. Bumping `carve-lang` now fails here until the snapshots are
regenerated with it, which puts the output change in the same diff as the
version change - which is what the note was for.

The comparison in `docs/comparisons/` is covered too. Its own README names no
version at all, and its `.md` files back a published capability table.
"""

from pathlib import Path

import carve
import pytest

from pdf_to_carve.pipeline import ConversionOptions, convert

ROOT = Path(__file__).parents[1]
SNAPSHOTS = sorted(
    [
        *(ROOT / "examples").glob("*/result.crv"),
        *(ROOT / "docs" / "comparisons").glob("*/*/result.crv"),
    ]
)


def test_the_snapshot_set_is_not_empty() -> None:
    """A glob that matches nothing would make every row below vacuous."""
    assert len(SNAPSHOTS) >= 7


@pytest.mark.parametrize(
    "source",
    SNAPSHOTS,
    ids=lambda path: f"{path.parent.parent.name}/{path.parent.name}",
)
def test_markdown_snapshot_matches_its_carve_source(source: Path) -> None:
    rendered = source.with_suffix(".md")
    assert rendered.is_file(), f"{rendered} is missing"
    expected = rendered.read_text(encoding="utf-8")
    actual = carve.to_markdown(source.read_text(encoding="utf-8"))
    assert actual == expected, (
        f"{rendered.relative_to(ROOT)} no longer matches {source.name} under the "
        "pinned engine. Regenerate it - `python examples/render_markdown.py "
        "examples/*/result.crv` for the examples - and review the diff as part of "
        "whatever moved the engine."
    )


COMPARISON = ROOT / "docs" / "comparisons" / "php-pdfparser-v3.3.0"


def test_the_comparison_carve_is_what_the_converter_writes_now(tmp_path: Path) -> None:
    """The published comparison's own side regenerates from its input PDF.

    The check above covers `.crv` to `.md`, and this covers the step before it.
    Without it the artifact aged out of the writer within the hour: a change to
    how ambiguous inline boundaries are spelled regenerated the examples and
    left this file behind, and nothing said so, because the only thing reading
    it renders it rather than producing it.

    Text mode is deterministic and local - no model, no network - so this is the
    same shape as `tests/test_pdf_corpus.py`, pointed at the document a
    published capability table is read off.

    `ours-hybrid/result.crv` is deliberately not here. It is a captured model
    run with no saved extraction JSON, so there is nothing to regenerate it
    from, and a test that cannot fail for the right reason is worse than none.
    """
    result = convert(
        COMPARISON / "input.pdf",
        ConversionOptions(mode="text", assets_dir=tmp_path / "assets"),
    )
    expected = (COMPARISON / "ours-text" / "result.crv").read_text(encoding="utf-8")
    assert result.source == expected, (
        "docs/comparisons/php-pdfparser-v3.3.0/ours-text/result.crv no longer "
        "matches what the writer produces. Regenerate it with the command in "
        "that directory's README and review the diff - the capability table "
        "beside it is read off this file."
    )
