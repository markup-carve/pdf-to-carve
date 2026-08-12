# pdf-to-carve

Convert born-digital PDFs, scanned PDFs, and document images into validated
[Carve](https://markup-carve.github.io/carve/) (`.crv`) source.

The conversion does **not** pass through Markdown and does not ask an AI model
to write Carve syntax. Extraction produces a small, validated JSON document;
a deterministic writer produces Carve.

```text
PDF/image -> text extraction or vision model -> document JSON -> Carve writer
                                                           -> carve fmt/lint
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
pdf-to-carve page.png --mode vision -o page.crv
```

Use `--base-url` with an OpenAI-compatible Chat Completions endpoint. The
configured model must accept image inputs and JSON-object response format.
Transient network, rate-limit, and server failures are retried three times by
default; adjust this with `--retries`.

Save the provider-neutral extraction result and replay it without an API call:

```bash
pdf-to-carve scan.pdf --mode vision --save-json scan.crv.json -o scan.crv
pdf-to-carve scan.crv.json --from-json -o rebuilt.crv
```

For the strongest check, point to the official Carve CLI. The command returns
exit status 2 if `carve fmt --check` or `carve lint` reports a problem:

```bash
pdf-to-carve document.pdf -o document.crv --carve-command carve
```

## When AI is used

AI is deliberately narrow and optional:

- Text PDFs use PyMuPDF and make no network request.
- Scans, images, and complex layouts use one document-level vision request.
- The model returns JSON, never executable content or final Carve syntax.
- JSON can be inspected, versioned, corrected, and replayed offline.
- No agents, embeddings, vector store, or automatic rewriting are involved.

Auto mode currently uses text coverage as its conservative routing signal.
Complex born-digital tables can still benefit from explicitly selecting
`--mode vision`.

## Extraction model

The version-1 model accepts headings, paragraphs, flat lists, code blocks,
quotes, tables, figures, thematic breaks, and page breaks. Inline content can
represent text, strong/emphasis/underline/strike, code, math, and links.
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
- Figure placeholders describe intended asset paths; automatic figure cropping
  is not part of 0.1.
- Very large PDFs may exceed a provider's request limits. Select a page range.
- PDF content is untrusted input. Review converted documents before publishing.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=pdf_to_carve --cov-report=term-missing
uv build
```

## License

MIT.
