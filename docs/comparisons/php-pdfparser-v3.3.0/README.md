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
pdf-to-carve input.pdf --mode text -o ours-text/result.crv
carve render --markdown ours-text/result.crv > ours-text/result.md
```

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
| Fenced code | Fence and indentation lost | Code block preserved; language and indentation lost |
| Simple table | Flattened text | Preserved as a table |
| Image | Labels become a heading | Labels remain plain text; image and alt text are lost |
| Literal Markdown punctuation | Several literals become markup | Preserved |

Our improved text mode is closer to the answer key on this fixture. It now
recovers the heading hierarchy, paragraph boundaries, styling, lists, code
block, simple table, super/subscript, link destination, underline, highlight,
blockquote, and literal punctuation. Their result still has the advantage of a
pure PHP deployment and direct Markdown output.

The deterministic result still loses code indentation and language, table
alignment hints, and image semantics. The PDF contains no visible code indent,
so reconstructing it would require inference rather than extraction. The image
is vector artwork rather than an embedded raster image.

## Additional hybrid reference

The captured hybrid run also recovers the PHP language and indentation. It
reconstructs the fully legible vector flow as editable Mermaid rather than
flattening its labels. It still loses the table's right-alignment hints. The
hybrid result uses a model, so it is intentionally excluded from the fair
PHP-only versus deterministic-text comparison.

## Performance

Sequential local observations from 23 August 2026, seven runs each:

| Extractor | Median | Range | Approx. peak RSS |
| --- | ---: | ---: | ---: |
| Their pure PHP PDF to Markdown | 0.15 s | 0.13 to 0.18 s | 43.5 MiB |
| Our PDFium PDF to Carve to Markdown | 0.36 s | 0.34 to 0.38 s | 67.1 MiB |

Their direct path is about 2.4 times faster and uses less memory than our
two-process PDF-to-Carve-to-Markdown route. These numbers include language and
CLI startup and apply only to this fixture and environment.

## Remaining local improvements

1. Preserve code indentation and infer a language only when visible evidence
   supports it.
2. Reconstruct raster and vector figures with reliable asset references.
3. Detect columns and other non-linear reading order.
4. Preserve table alignment and extend detection to spanning cells without
   guessing malformed grids.
5. Resolve internal PDF destinations in addition to external URI annotations.
