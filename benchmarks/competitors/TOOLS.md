# Tool provenance and eligibility

Versions are the versions actually used for the committed observations, not a
claim about each project's current release. Project links and license labels
are provided for auditability; dependency and model licenses may add terms.

| ID | Project | Measured version | Output path | License note |
| --- | --- | --- | --- | --- |
| `carve-hybrid` | [pdf-to-carve](https://github.com/markup-carve/pdf-to-carve) | commit `a23249a`, `gpt-5.6-sol` low | validated JSON → Carve | MIT project; measured backend and provider terms apply |
| `docling` | [Docling](https://github.com/docling-project/docling) | 2.119.0 | Markdown | MIT |
| `unstructured` | [Unstructured](https://github.com/Unstructured-IO/unstructured) | 0.25.2, fast strategy | plain text | Apache-2.0 |
| `carve-text` | [pdf-to-carve](https://github.com/markup-carve/pdf-to-carve) | commit `4d28758`, legacy backend | Carve | MIT project; backend terms noted in `runs.json` |
| `markitdown` | [Microsoft MarkItDown](https://github.com/microsoft/markitdown) | 0.1.7 | Markdown | MIT |
| `marker` | [Marker](https://github.com/datalab-to/marker) | 2.0.0 | Markdown | Apache-2.0 code; model terms apply |
| `mineru` | [MinerU](https://github.com/opendatalab/MinerU) | 3.4.4 | Markdown | custom MinerU Open Source License, based on Apache-2.0 with additional conditions |
| `pymupdf4llm` | [PyMuPDF4LLM](https://github.com/pymupdf/RAG) | 1.28.2 | Markdown | AGPL-3.0 or commercial |
| `carve-claude-sonnet` | [pdf-to-carve](https://github.com/markup-carve/pdf-to-carve) via Claude Code | CLI 2.1.228, Claude Sonnet 5 low | validated JSON → Carve | MIT project; provider terms apply |
| `carve-claude-opus` | [pdf-to-carve](https://github.com/markup-carve/pdf-to-carve) via Claude Code | CLI 2.1.228, Claude Opus 5 low | validated JSON → Carve | MIT project; provider terms apply |
| `markpdfdown` | [MarkPDFdown](https://github.com/MarkPDFdown/markpdfdown) | 1.1.2, commit `4b38fd8f91bd5cd61181bd3c68bf025f6040115b`, `gpt-4o` | Markdown | Apache-2.0 project; required backend and provider terms also apply |

## Why Pandoc is not a scored extractor

[Pandoc](https://pandoc.org/) is part of the wider conversion landscape, but it
does not provide a PDF input reader. It can convert Markdown or other supported
source formats after extraction, and it can produce PDFs as output; treating it
as a PDF extractor would require an unreported upstream OCR/extraction stage and
would score that stage instead of Pandoc. It is therefore recorded as ineligible
for this PDF-to-editable-markup benchmark rather than shown as a zero.

## Version drift

Some projects have changed licenses, defaults, model weights, or extraction
pipelines since the measured versions. Reproduction should use isolated,
version-pinned environments and assess the full dependency graph. A future run
against newer versions belongs in a new dated result rather than silently
overwriting this observation.
