# Why Carve over Markdown?

Markdown is an excellent interchange format for simple prose. PDF recovery is
not limited to simple prose: documents contain captions, spanning tables,
equations, admonitions, editorial changes, diagrams, charts, attributes, and
cross-references. Carve is the stronger destination when those distinctions
must remain editable and mechanically verifiable.

## The short answer

Use Markdown when broad compatibility and a minimal feature set matter most.
Use Carve when document structure, deterministic output, validation, and
multiple rendering targets matter more than accepting the lowest common
denominator.

`pdf-to-carve` does not rely on a vision model to spell Carve correctly:

```text
PDF/image -> text extraction or vision model -> document JSON -> Carve writer
                                                           -> carve fmt/lint
```

The model identifies document meaning. A strict validator and deterministic
writer own the syntax.

## What survives in Carve

| Document feature | Carve destination | Typical Markdown destination |
|---|---|---|
| Rowspan and colspan | Native table cells | Empty placeholder cells or raw HTML |
| Figure/table captions | Native captions | Nearby italic paragraphs |
| Admonitions | Native typed blocks | Block quotes or flavor-specific extensions |
| Math | Defined native syntax | Flavor/plugin-dependent syntax |
| Insert/delete/substitute | Native critic markup | Styling or raw HTML; substitution relationship is lost |
| Super/subscript/highlight/underline | Native inline nodes | Raw HTML or flavor-dependent extensions |
| Diagram and chart source | Typed fenced blocks | Fences are possible, but semantics depend on the host |
| Cross-references | Native resolution and numbering | Manual links and labels |
| Arbitrary attributes | Uniform element attributes | Usually raw HTML or extensions |

Markdown can visually approximate many of these. Approximation is different
from retaining a typed structure that downstream tooling can inspect, validate,
transform, and render consistently.

## Validation changes the failure mode

A visually plausible transcription can still be structurally impossible—for
example, a four-column table row that accounts for only three columns.

The structured Carve path rejects that output with an exact JSON path before it
can become a misleading document. It also supports explicit logical
`rowspan`/`colspan` cells, verifies the complete grid, emits native Carve
placeholders, and runs the official formatter and linter.

For unattended imports, a clear failure is safer than a successful process that
produces an empty or silently flattened document.

## Evidence, not just expressiveness

In the current equal-model complex-PDF benchmark, Structured Carve beats the
Markdown baseline on every non-ceiling measurement:

| Fixture | Structured Carve | Markdown baseline |
|---|---:|---:|
| Feature showcase, character similarity | **0.976** | 0.890 |
| Feature showcase, word similarity | **0.956** | 0.827 |
| Math/diagrams/charts, character similarity | **0.974** | 0.822 |
| Math/diagrams/charts, word similarity | **0.871** | 0.771 |
| Native table spans | **2/2** | 0/2 |
| Editable diagram/chart sources | **3/3** | 1/3 as generic text |

Both paths recover all three equations and can ultimately produce valid Carve;
the structured path reaches valid Carve directly. Read the full
[methodology, side-by-side analysis, and limitations](vision-benchmark-2026-08.md).

## Where Markdown still wins

Markdown has wider native support across existing websites, editors, and APIs.
It is easier to paste into systems that know nothing about Carve, and models
have seen much more Markdown during training.

That is why Carve includes Markdown conversion and Markdown rendering. Choosing
Carve as the structured source does not require abandoning Markdown as an
interop target.

## Scope of the claim

The benchmark currently contains two known-truth complex documents. The result
supports choosing Carve for this pipeline; it is not proof that every model,
language, scan quality, or layout will score the same way. Scanned,
multi-column, multilingual, and repeated-run fixtures are the next evidence
needed.

