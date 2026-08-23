# Conversion examples

These compact, self-generated examples make format capabilities and extraction
trade-offs inspectable without an API key. All example content is dedicated to
the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

| Example | Challenge | Input | Carve | Markdown | Ground truth |
| --- | --- | --- | --- | --- | --- |
| Scientific paper | Columns, equation, footnote, table | [PDF](scientific-paper/input.pdf) | [Carve](scientific-paper/result.crv) | [Markdown](scientific-paper/result.md) | [JSON](scientific-paper/extraction.json) |
| Financial report | Numeric table and warning | [PDF](financial-report/input.pdf) | [Carve](financial-report/result.crv) | [Markdown](financial-report/result.md) | [JSON](financial-report/extraction.json) |
| Editorial review | Substitution, deletion, insertion, admonition | [PDF](editorial-review/input.pdf) | [Carve](editorial-review/result.crv) | [Markdown](editorial-review/result.md) | [JSON](editorial-review/extraction.json) |

`extraction.json` is hand-authored ground truth, not a claim about a particular
model run. `result.crv` is generated deterministically from it, then `result.md`
is generated from that Carve source by Carve's own Markdown writer. This dogfoods
Carve's real degradation path rather than maintaining a favorable second renderer
here. The comparison therefore isolates format expressiveness from extraction
accuracy. Each example README notes where the Markdown export needs HTML,
conventions, extensions, or loses semantics.

Regenerate the PDFs and both outputs:

```bash
python examples/generate_pdfs.py
for case in examples/*/extraction.json; do
  pdf-to-carve "$case" --from-json -o "${case%/extraction.json}/result.crv"
done
python examples/render_markdown.py examples/*/result.crv
```

## Which Carve renders these

The Markdown step uses `carve-lang`, the PyO3 binding over carve-rs, pinned to an
exact version in `pyproject.toml` and resolved in `uv.lock`. `uv sync --extra dev`
installs it; nothing else is needed.

The renderer used to be `@markup-carve/carve` through a Node script, which is why
this section used to name a Carve JS revision by hand. Two engines at two
versions, one of them recorded only in prose: the snapshots aged two releases
behind while the note beside them still read as current, and by then the export
had stopped escaping a bare percent and had learned to carry a table caption that
two example READMEs still described as lost.

One pinned engine now serves the snapshots and the conformance gate alike, so
there is one version to read and Renovate can see it. `tests/test_example_snapshots.py`
regenerates every committed `.md` from its `.crv` and fails when they disagree -
which is what makes the pin worth recording, rather than the recording itself.
