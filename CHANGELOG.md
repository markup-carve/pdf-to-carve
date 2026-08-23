# Changelog

## Unreleased

### Conversion

- Improve deterministic PDFium text extraction with document-relative heading
  levels, paragraph line joining, font-run styling, super/subscript, conservative
  unordered and ordered lists, monospaced code blocks, and simple table grids.

### Output

- Escape literal block-opening punctuation before it can become unintended
  Carve headings, lists, quotes, containers, tables, or thematic breaks.

## 0.1.0 - 2026-08-12

First release.

### Conversion

- Convert born-digital PDFs with no AI involved: text, layout, and structure come
  from the PDF itself.
- Convert scans and document images through an optional OpenAI-compatible vision
  path, and pick per page automatically in `auto` mode.
- Add a hybrid mode that sends rendered pages together with positioned text
  evidence, for born-digital PDFs whose layout survives rendering better than
  extraction.
- Add opt-in authenticated CLI providers for when API billing is unavailable -
  Codex CLI and Claude CLI - each with isolated image access, permission-denial
  checks, and local validation of the returned JSON.

### Output

- Emit Carve through a deterministic writer over a strict, versioned extraction
  document - the model never writes Carve syntax - and verify the result with
  the official `carve fmt` / `carve lint` CLI when it is available.
- Emit native Carve math, canonical thematic and page breaks, logical table
  cells with validated rowspan/colspan grids, highlight, super/subscript, critic
  markup, footnotes, and admonitions.
- Recover legible diagrams and charts as editable typed code blocks rather than
  dropping them.
- Preserve plain underscores in figure alt text.

### Working with a conversion

- Save the provider-neutral extraction JSON and replay it without a second API
  call (`--save-json`, `--from-json`).
- Select pages (`--start-page`, `--end-page`) and cache provider responses by
  content (`--cache-dir`).
- Generate a self-contained, escaped HTML review report, and extract embedded
  raster assets.

### Safety and licensing

- Bound input size, page count, DPI, and provider-response size.
- Record per-block provenance, confidence, warnings, and evidence.
- Default to the permissively licensed PDFium backend, with PyMuPDF kept as an
  optional extra.
