"""Render each example's Carve source to Markdown with the pinned engine.

DOGFOODS CARVE'S OWN MARKDOWN WRITER, so what the examples show is the real
degradation path and not a second renderer maintained here to flatter it.

The engine is `carve-lang`, the PyO3 binding over carve-rs, pinned as a dev
dependency in `pyproject.toml`. It used to be `@markup-carve/carve` through a
Node script, which meant the repository carried two Carve engines at two
versions - the tests' and the snapshots' - and only one of them was pinned
anywhere a tool could read. The snapshots then sat two releases behind without
anything noticing: they still escaped a bare percent and still dropped a table
caption that Carve had learned to export, and two example READMEs described
that loss as a property of Markdown.

`tests/test_example_snapshots.py` regenerates and compares, so a snapshot that
stops matching its source fails a gate rather than aging quietly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import carve


def render(paths: list[str]) -> None:
    if not paths:
        raise SystemExit("usage: python examples/render_markdown.py CASE/result.crv [...]")
    for raw in paths:
        source = Path(raw)
        if source.name != "result.crv":
            raise SystemExit(f"expected a result.crv path: {raw}")
        source.with_suffix(".md").write_text(
            carve.to_markdown(source.read_text(encoding="utf-8")), encoding="utf-8"
        )


if __name__ == "__main__":
    render(sys.argv[1:])
