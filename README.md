# pdf-to-carve

Convert born-digital PDFs, scanned PDFs, and document images into validated
[Carve](https://markup-carve.github.io/carve/) (`.crv`) source.

The conversion does **not** pass through Markdown and does not ask an AI model
to write Carve syntax. Extraction produces a small, validated JSON document;
a deterministic writer produces Carve.

See [Why Carve over Markdown?](docs/why-carve-over-markdown.md) and the
[equal-model complex-PDF benchmark](docs/vision-benchmark-2026-08.md). The
[conversion examples](examples/README.md) provide small before-and-after PDFs,
validated JSON, Carve, and Markdown for direct inspection.

For the broader extractor comparison, see the
[reproducible competitor benchmark](benchmarks/competitors/REPORT.md), including
raw normalized outputs, pinned versions, completion failures, scoring code, and
methodological limitations.

```text
PDF/image -> text, vision, or hybrid extraction -> document JSON -> Carve writer
                                                               -> carve fmt/lint
                                                               -> review report
```

## Install

Python 3.10 or newer is required.

```bash
pip install pdf-to-carve
```

For development:

```bash
git clone https://github.com/markup-carve/pdf-to-carve.git
cd pdf-to-carve
uv sync --extra dev
```

## Use

Auto mode uses deterministic PDF text extraction when a page has enough usable
text, otherwise it selects vision:

```bash
pdf-to-carve document.pdf -o document.crv
```

Force a mode or select pages:

```bash
pdf-to-carve document.pdf --mode text --start-page 2 --end-page 8
OPENAI_API_KEY=... pdf-to-carve scan.pdf --mode vision --model gpt-4o-mini
OPENAI_API_KEY=... pdf-to-carve complex.pdf --mode hybrid --cache-dir .cache/pdf-to-carve
pdf-to-carve complex.pdf --mode hybrid --provider codex-cli --model gpt-5.6-sol
pdf-to-carve page.png --mode vision -o page.crv
```

Hybrid mode sends both rendered pages and positioned text evidence. It is useful
for complex born-digital PDFs where text extraction preserves spelling but loses
layout. Vision requests are capped at 20 pages by default; use `--max-pages` and
`--dpi` to tune the request explicitly.

`--provider codex-cli` uses an existing authenticated Codex CLI installation
when API billing is unavailable. It launches an ephemeral, read-only session,
ignores repository rules and user configuration, validates the returned JSON
locally, and otherwise uses the same hybrid pipeline. This is still a remote AI
request—not local inference—and requires an image-capable Codex model.

Use `--base-url` with an OpenAI-compatible Chat Completions endpoint. The
configured model must accept image inputs and JSON-object response format.
Transient network, rate-limit, and server failures are retried three times by
default; adjust this with `--retries`.

Save the provider-neutral extraction result and replay it without an API call:

```bash
pdf-to-carve scan.pdf --mode vision --save-json scan.crv.json -o scan.crv
pdf-to-carve scan.crv.json --from-json -o rebuilt.crv
```

Generate a self-contained local review report and extract embedded raster assets:

```bash
pdf-to-carve report.pdf --mode hybrid -o report.crv \
  --review-html review.html --assets-dir assets --save-json report.crv.json
```

The report escapes all document content and includes the generated source,
validated JSON, provenance coverage, and warning count. See the
[review workflow](docs/review-workflow.md).

For the strongest check, point to the official Carve CLI. The command returns
exit status 2 if `carve fmt --check` or `carve lint` reports a problem:

```bash
pdf-to-carve document.pdf -o document.crv --carve-command carve
```

## When AI is used

AI is deliberately narrow and optional:

- Text PDFs use PDFium by default and make no network request.
- Scans, images, and complex layouts use one document-level vision request.
- Hybrid mode gives the model bounded positioned-text evidence alongside images.
- The model returns JSON, never executable content or final Carve syntax.
- JSON can be inspected, versioned, corrected, and replayed offline.
- No agents, embeddings, vector store, or automatic rewriting are involved.

Auto mode currently uses text coverage as its conservative routing signal.
Complex born-digital tables can still benefit from explicitly selecting
`--mode vision`.

## Extraction model

The version-1 model accepts headings, paragraphs, flat lists, code blocks,
quotes, admonitions, spanning tables, figures, thematic breaks, and page breaks.
Inline content can represent text, common decoration, super/subscript, critic
markup, inline footnotes, code, math, and links.
Optional provenance records associate a block with a page, bounding box,
confidence, warnings, and short evidence for review without affecting Carve output.
Unknown fields and malformed nodes fail closed with a precise JSON path.
The machine-readable contract is
[`document-v1.schema.json`](src/pdf_to_carve/document-v1.schema.json).

This is intentionally smaller than the complete Carve AST. It describes what
document extraction can establish reliably, while the writer owns syntax and
escaping. The contract can evolve by adding a new version.

## Limitations

- Deterministic text mode infers headings from font size; it does not reconstruct
  tables, lists, images, columns, or inline styling yet.
- Vision accuracy and cost depend on the selected provider and model.
- `--assets-dir` extracts and deduplicates embedded raster images. Figure cropping
  and exact model-placeholder matching remain manual review steps.
- Very large PDFs may exceed a provider's request limits. Select a page range.
- PDF content is untrusted input. Review converted documents before publishing.

See [privacy and security](docs/privacy-security.md) before processing sensitive files.
For distribution planning, see the
[PDF backend licensing options](docs/dependency-licensing.md).

The default PDFium backend is permissively licensed. Install the optional
PyMuPDF compatibility backend when exact legacy behavior is required:

```bash
pip install 'pdf-to-carve[pymupdf]'
pdf-to-carve document.pdf --pdf-backend pymupdf
```

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=pdf_to_carve --cov-report=term-missing
uv build
```
