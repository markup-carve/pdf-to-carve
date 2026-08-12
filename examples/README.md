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
is generated from that Carve source by the official `carveToMarkdown` renderer.
This dogfoods Carve's real degradation path rather than maintaining a favorable
second renderer here. The comparison therefore isolates format expressiveness
from extraction accuracy. Each example README notes where the Markdown export
needs HTML, conventions, extensions, or loses semantics.

Regenerate the PDFs and Carve outputs:

```bash
python examples/generate_pdfs.py
for case in examples/*/extraction.json; do
  pdf-to-carve "$case" --from-json -o "${case%/extraction.json}/result.crv"
done
node examples/render_markdown.mjs examples/*/result.crv
```

The Markdown step requires `@markup-carve/carve`, available in the Carve JS
repository or from its package installation.

The committed Markdown snapshots were generated with Carve JS `0.1.0`
(`c5760e2ad712bb2bea5ab2b6fb85916725f7ffd3`). Recording the renderer pin keeps
future output changes attributable and reviewable.
