# Local PDF text extraction comparison

This is the fair no-AI comparison between `prinsfrank/pdfparser` v3.3.0 and
`pdf-to-carve --mode text`.

Both read the existing PDF text layer locally and deterministically. Neither
sends the document to a model or network service. Their implementation is pure
PHP. Ours is Python and uses PDFium through `pypdfium2`, so the deployment
requirements are not identical.

## Files

- [`input.pdf`](input.pdf): the two-page input.
- [`ground-truth/result.md`](ground-truth/result.md): the hand-written Markdown
  answer key used to create the PDF.
- [`theirs/result.raw.md`](theirs/result.raw.md): their direct `getMarkdown()`
  result.
- [`theirs/result.md`](theirs/result.md): their result normalized through
  `Markdown -> Carve -> Markdown` for a common final renderer.
- [`ours-text/result.crv`](ours-text/result.crv): our local extraction result.
- [`ours-text/result.md`](ours-text/result.md): our result rendered through the
  official Carve Markdown writer.
- [`ours-hybrid/result.crv`](ours-hybrid/result.crv): one captured hybrid result
  using rendered pages, positioned PDF evidence, and `gpt-5.6-sol`.
- [`ours-hybrid/result.md`](ours-hybrid/result.md): that hybrid result rendered
  through the official Carve Markdown writer. It is an additional reference,
  not part of the no-AI comparison.

## Commands

Their extraction:

```php
$document = (new PdfParser())->parseFile('input.pdf');
$markdown = $document->getMarkdown();
```

Our extraction:

```bash
pdf-to-carve input.pdf --mode text --assets-dir ours-text/assets -o ours-text/result.crv
python ../../../examples/render_markdown.py ours-text/result.crv
```

Every `result.md` here is rendered by Carve's own Markdown writer through
`carve-lang`, pinned in `pyproject.toml`, and `tests/test_example_snapshots.py`
regenerates all four and fails when one stops matching its `.crv`. The step used
to be an unversioned `carve --markdown`, which left the capability table below
resting on whichever engine happened to be on the author's PATH.

## Result

| Capability | Their v3.3.0 | Our improved text mode |
| --- | --- | --- |
| H1/H2 hierarchy | H4/H5 | Correct H1/H2 |
| Wrapped paragraphs | Lines and paragraphs merge | Correctly joined and separated |
| Bold and italic | Preserved | Preserved |
| Superscript/subscript | Lost or displaced | Preserved |
| Underline/highlight | Lost | Preserved |
| Link label | Preserved | Preserved |
| Link URL | Lost | Preserved from the PDF annotation |
| Unordered list | Markers lost | Preserved |
| Ordered list | Preserved | Preserved |
| Blockquote | Becomes italic text | Preserved |
| Fenced code | Fence and indentation lost | Code block and strongly evidenced PHP language preserved; indentation absent |
| Simple table | Flattened text | Preserved with right-aligned numeric columns |
| Image | Labels become a heading | Vector appearance preserved as a PNG with visible-label alt text |
| Literal Markdown punctuation | Several literals become markup | Preserved |

Our improved text mode is closer to the answer key on this fixture. It now
recovers the heading hierarchy, paragraph boundaries, styling, lists, code
block, code language, simple table and alignment, super/subscript, link destination,
underline, highlight, blockquote, vector figure appearance, visible-label alt text,
and literal punctuation. Their result still has the advantage of a
pure PHP deployment and direct Markdown output.

The deterministic result still leaves the code unindented because the second
code line starts slightly to the left of the first in the PDF. Reindenting it
would be source-code normalization rather than extraction. It preserves the
vector diagram's appearance and visible labels, but does not claim editable
boxes-and-arrows semantics.

## Additional hybrid reference

The captured hybrid run also recovers the indentation. It
reconstructs the fully legible vector flow as editable Mermaid rather than
flattening its labels. It still loses the table's right-alignment hints. The
hybrid result uses a model, so it is intentionally excluded from the fair
PHP-only versus deterministic-text comparison.

## Performance

Sequential local observations from 23 August 2026, seven runs each:

| Extractor | Median | Range | Approx. peak RSS |
| --- | ---: | ---: | ---: |
| Their pure PHP PDF to Markdown | 0.19 s | 0.15 to 0.26 s | 43.7 MiB |
| Our PDFium PDF to Carve to Markdown | 0.43 s | 0.36 to 0.63 s | 52.6 MiB |

Their direct path is about 2.3 times faster and uses less memory than our
two-process PDF-to-Carve-to-Markdown route. These numbers include language and
CLI startup, plus vector-asset preservation on our path, and apply only to this
fixture and environment.

## Remaining local improvements

1. Offer explicit source-code normalization separately from faithful extraction.
2. Associate embedded raster figures with their document positions.
3. Detect columns and other non-linear reading order.
4. Extend table detection to spanning cells without guessing malformed grids.
5. Resolve internal PDF destinations in addition to external URI annotations.
