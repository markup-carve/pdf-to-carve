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
| Feature showcase: character similarity | rejected | **0.890** | Markdown wins on immediate usability |
| Feature showcase: word similarity | rejected | **0.827** | Markdown wins |
| Math/diagrams/charts: character similarity | **0.831** | 0.822 | Carve by 0.009 |
| Math/diagrams/charts: word similarity | **0.790** | 0.771 | Carve by 0.019 |
| Equations recovered | 3/3 | 3/3 | tie |
| Valid final Carve, math fixture | yes | yes after deterministic import | tie |

“Rejected” is intentional fail-closed behavior. The vision model returned three
cells for the final row of a four-column spanning table. The version-1
extraction contract requires every row to account for all columns, so conversion
stopped at the exact path:

```text
document.blocks[6].rows[2] must have 4 cells
```

The Markdown table used empty placeholder cells and remained usable, although
Markdown cannot express the original rowspan/colspan semantics. It looked
rectangular but had lost the spans.

## Side-by-side structural analysis

### Feature showcase

| Construct | Ground truth | Structured Carve | Markdown baseline |
|---|---|---|---|
| Heading hierarchy | 1 H1 + 3 H2 | recovered | recovered |
| Inline emphasis | strong, emphasis, underline, strike, highlight, bold-italic | mostly recovered; one critic replacement misread | visually recovered, but underline/critic semantics degraded through HTML-like markup |
| Table | 4 columns with rowspan and colspan | recognized as a table, then rejected because a spanning row was structurally incomplete | valid rectangular table; spans lost |
| Figure | image + caption | explicit figure node and caption | image placeholder + italic caption |
| Admonition | semantic admonition | flattened to strong “Note” plus paragraph | represented as block quote |
| Quotation | quote + attribution | explicit quote and attribution | block quote with em-dash attribution |
| Footnote | semantic inline footnote/endnote | emitted as an ordered-list endnote | emitted as a footnote definition |
| Mechanical result | — | no `.crv`, precise validation error | usable Markdown |

The baseline is more forgiving here. The structured path retains stronger node
intent, but its v1 table model has no explicit span cell and therefore cannot
represent the model's partial spanning row safely. Padding the row silently
would improve completion rate while fabricating structure, so rejection is the
right current behavior.

### Math, diagrams, and charts

| Construct | Ground truth | Structured Carve | Markdown baseline |
|---|---|---|---|
| Heading hierarchy | 1 H1 + 3 H2 | exact | exact |
| Equations | 2 inline + 1 display | all three recovered as math nodes | all three recovered as math |
| First diagram | Mermaid source | figure with descriptive alt text | bold text and arrows |
| Second diagram | Mermaid source | figure with full pipeline alt text | text code block approximating layout |
| Chart | Chart.js source and rendered chart | figure with title and all four values in alt text | semantic two-column data table with all four values |
| Repeated page chrome | present in PDF | top kicker and final byline retained | same |
| Final validity | — | canonical and lint-clean | valid after Markdown import |

The structured result slightly wins text similarity and produces explicit
figure nodes, which is useful for downstream asset workflows. The Markdown
result represents the chart data more editably as a table and the second
diagram more readably as text. Neither can reconstruct the original Mermaid or
Chart.js source from pixels; claiming otherwise would be hallucination.

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

The benchmark exposed three Carve-writer defects that unit fixtures had not:

1. Math was initially emitted as Markdown-style `$…$` instead of native Carve
   math (`$` followed by a verbatim span).
2. The thematic-break writer emitted a valid alternative spelling rather than
   the canonical spelling.
3. Figure alt text over-escaped underscores, changing canonical output.

All three now have regression tests. An earlier multi-page run also found and
fixed noncanonical empty page-break container layout.

## Conclusion

There is no universal winner yet.

- The Markdown path is currently more tolerant of structurally incomplete
  vision output and won the spanning-table fixture.
- The structured Carve path was slightly more faithful on the math/visual
  fixture, retains explicit typed nodes, and fails safely when either model
  output or provider execution is invalid.
- Carve's language advantages matter most after extraction: native captions,
  richer tables, typed figures, math, attributes, and deterministic validation
  provide a better destination than Markdown can express. They do not by
  themselves guarantee better OCR.

The highest-value next step is explicit `rowspan`/`colspan` support in the
extraction contract and serializer, followed by a larger corpus with scanned,
multi-column, and non-English documents.

