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
| Underline/highlight | Lost | Lost |
| Link label | Preserved | Preserved |
| Link URL | Lost | Lost |
| Unordered list | Markers lost | Preserved |
| Ordered list | Preserved | Preserved |
| Blockquote | Becomes italic text | Becomes italic text |
| Fenced code | Fence and indentation lost | Code block preserved; language and indentation lost |
| Simple table | Flattened text | Preserved as a table |
| Image | Labels become a heading | Labels remain plain text; image and alt text are lost |
| Literal Markdown punctuation | Several literals become markup | Preserved |

Our improved text mode is closer to the answer key on this fixture. It now
recovers the heading hierarchy, paragraph boundaries, styling, lists, code
block, simple table, super/subscript, and literal punctuation. Their result
still has the advantage of a pure PHP deployment and direct Markdown output.

Neither local extractor recovers the PDF link annotation, image semantics,
underline, or highlight. Neither can reliably distinguish the visually italic
blockquote from a normal italic paragraph using text evidence alone.

## Performance

Sequential local observations from 23 August 2026, seven runs each:

| Extractor | Median | Range | Approx. peak RSS |
| --- | ---: | ---: | ---: |
| Their pure PHP PDF to Markdown | 0.15 s | 0.13 to 0.18 s | 43.5 MiB |
| Our PDFium PDF to Carve | 0.23 s | 0.21 to 0.31 s | 36.1 MiB |
| Our PDFium PDF to Carve to Markdown | 0.36 s | 0.34 to 0.38 s | 67.1 MiB |

For extraction alone, their median is about 1.5 times faster and ours uses about
17 percent less peak memory. Comparing final Markdown output, their direct path
is about 2.4 times faster and uses less memory than our two-process
PDF-to-Carve-to-Markdown route. These numbers include language and CLI startup
and apply only to this fixture and environment.

## Remaining local improvements

1. Read PDF link annotations and match them to text rectangles.
2. Detect underline and highlight from page drawing objects.
3. Preserve code indentation and infer a language only when visible evidence
   supports it.
4. Extract embedded images and associate them with nearby captions/alt text.
5. Add conservative quote detection when indentation and font evidence agree.
6. Extend table detection to spanning cells without guessing malformed grids.
