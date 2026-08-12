# Conversion examples

These compact, self-generated examples make format capabilities and extraction
trade-offs inspectable without an API key. All example content is dedicated to
the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

| Example | Challenge | Input | Carve | Markdown | Ground truth |
| --- | --- | --- | --- | --- | --- |
| Scientific paper | Columns, equation, footnote, table | [PDF](scientific-paper/input.pdf) | [Carve](scientific-paper/expected.crv) | [Markdown](scientific-paper/expected.md) | [JSON](scientific-paper/extraction.json) |
| Financial report | Numeric table and warning | [PDF](financial-report/input.pdf) | [Carve](financial-report/expected.crv) | [Markdown](financial-report/expected.md) | [JSON](financial-report/extraction.json) |
| Editorial review | Substitution, deletion, insertion, admonition | [PDF](editorial-review/input.pdf) | [Carve](editorial-review/expected.crv) | [Markdown](editorial-review/expected.md) | [JSON](editorial-review/extraction.json) |

`extraction.json` is hand-authored ground truth, not a claim about a particular
model run. Both textual outputs represent that same ground truth so the comparison
isolates format expressiveness from extraction accuracy. Each example README notes
where ordinary Markdown needs HTML, conventions, or loses semantics.

Regenerate the PDFs and Carve outputs:

```bash
python examples/generate_pdfs.py
for case in examples/*/extraction.json; do
  pdf-to-carve "$case" --from-json -o "${case%/extraction.json}/expected.crv"
done
```
