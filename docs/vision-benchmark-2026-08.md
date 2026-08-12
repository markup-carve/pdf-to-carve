# Vision-first PDF import benchmark — August 2026

This benchmark compares two ways to turn visually complex PDF pages into
editable markup while holding the vision model and page images constant:

- **Structured Carve:** page images → validated document JSON → deterministic
  Carve writer.
- **Markdown baseline:** page images → Markdown generated directly by the
  vision model.

This is a small diagnostic benchmark, not a general model leaderboard. Its
purpose is to expose representation and pipeline behavior on constructs that
plain prose tests miss.

## Method

| Setting | Value |
|---|---|
| Vision model | `gpt-5.6-sol`, reasoning effort `low` |
| Rasterization | PNG, 160 DPI |
| Carve validation | extraction contract v1, then `carve fmt --check` and `carve lint` |
| Ground truth | The `.crv` files from which the PDFs were rendered |
| Text score | `SequenceMatcher`, after collapsing whitespace; character and word sequence ratios |
| Prompt policy | Preserve wording/order/structure; omit repeating headers, footers, and page numbers |

The source fixtures are the one-page
[feature showcase](https://github.com/markup-carve/carve-pdf/blob/master/examples/02-showcase.crv)
and the three-page
[math, diagrams, and charts document](https://github.com/markup-carve/carve-pdf/blob/master/examples/03-math-diagrams.crv).
They exercise inline formatting, a spanning table, a figure and caption,
footnotes, critic markup, an admonition, a quotation, three equations, two
diagrams, and a chart.

The scores compare rendered plain text, not source punctuation. Structural
counts come from parsed Carve ASTs. For the Markdown path, Markdown was first
converted with Carve's deterministic Markdown importer, then parsed like the
native output.

## Results

| Fixture | Structured Carve | Markdown baseline | Outcome |
|---|---:|---:|---|
| Feature showcase: character similarity | **0.976** | 0.890 | Carve by 0.086 |
| Feature showcase: word similarity | **0.956** | 0.827 | Carve by 0.129 |
| Math/diagrams/charts: character similarity | **0.974** | 0.822 | Carve by 0.152 |
| Math/diagrams/charts: word similarity | **0.871** | 0.771 | Carve by 0.100 |
| Equations recovered | 3/3 | 3/3 | tie |
| Native table spans recovered | **2/2** | 0/2 | Carve |
| Editable diagram/chart sources | **3/3** | 1/3 as generic text | Carve |
| Native semantic nodes, showcase | **all tested kinds** | partial | Carve |
| Valid final Carve | **direct** | yes after deterministic import | Carve has fewer stages |

The first structured run correctly rejected an incomplete spanning row. That
finding led to explicit logical cells with `rowspan`/`colspan` in the extraction
contract. The rerun recovered both spans and still validates that every logical
row covers the complete grid. The Markdown table remained rectangular by using
empty placeholders, but it could not retain either span.

## Side-by-side structural analysis

### Feature showcase

| Construct | Ground truth | Structured Carve | Markdown baseline |
|---|---|---|---|
| Heading hierarchy | 1 H1 + 3 H2 | recovered | recovered |
| Inline emphasis | strong, emphasis, underline, strike, highlight, bold-italic | recovered as native nodes | visually recovered, with some semantics routed through HTML-like markup |
| Super/subscript | one of each | native nodes | visually represented |
| Critic markup | insertion, deletion, substitution | all three native operations | insertion/deletion styling; substitution relationship lost |
| Table | 4 columns with rowspan and colspan | valid native table with both spans | valid rectangular table; spans lost |
| Figure | image + caption | explicit figure node and caption | image placeholder + italic caption |
| Admonition | semantic admonition | native admonition | represented as block quote |
| Quotation | quote + attribution | explicit quote and attribution | block quote with em-dash attribution |
| Footnote | semantic inline footnote/endnote | native inline footnote | footnote definition |
| Mechanical result | — | canonical, lint-clean Carve | usable Markdown; valid Carve after a second conversion |

The structured path now preserves every semantic category exercised by the
fixture. Importantly, it did not achieve this by padding an incomplete table:
the model emits logical spanning cells and the validator checks the resulting
grid before the writer runs.

### Math, diagrams, and charts

| Construct | Ground truth | Structured Carve | Markdown baseline |
|---|---|---|---|
| Heading hierarchy | 1 H1 + 3 H2 | exact | exact |
| Equations | 2 inline + 1 display | all three recovered as math nodes | all three recovered as math |
| First diagram | Mermaid source | editable Mermaid with all nodes/edges | bold text and arrows |
| Second diagram | Mermaid source | editable Mermaid with all nodes/edges | generic text code block approximating layout |
| Chart | Chart.js source and rendered chart | editable Chart.js JSON with type, title, labels, series, values, and colors | semantic two-column data table with all four values |
| Repeated page chrome | present in PDF | omitted | retained |
| Final validity | — | canonical and lint-clean | valid after Markdown import |

The structured result reconstructs minimal equivalent diagram/chart source only
when every visible label, edge, and value is legible. This is semantic recovery,
not byte-for-byte recovery of hidden source: the chart color differs slightly
from the original and generated node identifiers are new. The visible topology,
labels, values, chart type, and title match.

## Failure behavior under provider exhaustion

A separate API smoke test used a valid key on an account with no remaining
credits. It measured operational behavior only; no fidelity result came from
that test.

| Behavior after retries | Structured Carve | Markdown baseline |
|---|---|---|
| Process exit | nonzero | zero |
| Output | none | empty file |
| User-facing status | explicit HTTP 429 failure | reported successful completion after logging page failures |

For automation, the structured pipeline's fail-closed behavior is materially
safer: an empty document cannot be mistaken for a successful transcription.

## Defects found by the benchmark

The benchmark exposed Carve-writer and extraction-contract defects that unit
fixtures had not:

1. Math was initially emitted as Markdown-style `$…$` instead of native Carve
   math (`$` followed by a verbatim span).
2. The thematic-break writer emitted a valid alternative spelling rather than
   the canonical spelling.
3. Figure alt text over-escaped underscores, changing canonical output.
4. Fenced code info strings omitted Carve's canonical separating space.
5. The extraction vocabulary lacked explicit table spans and several native
   semantic nodes visible in the fixture.

All five now have regression tests. An earlier multi-page run also found and
fixed noncanonical empty page-break container layout.

## Conclusion

Structured Carve wins every non-ceiling metric in this corpus and ties the
ceiling cases (equation recovery and final validity). Its largest gains come
from asking the model for semantics that Carve can represent directly, then
making a deterministic writer—not the model—own syntax.

This does not prove universal OCR superiority. It proves that on these two
known-truth fixtures, with the same model and page images, the richer structured
destination improves both measured text fidelity and native structural
recovery. A larger corpus with scans, multi-column layouts, multiple languages,
and repeated runs is still required before generalizing the result.
