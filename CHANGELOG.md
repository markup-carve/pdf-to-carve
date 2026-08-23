# Changelog

## 0.1.2 - 2026-08-23

### Conversion

- Improve deterministic PDFium text extraction with document-relative heading
  levels, paragraph line joining, font-run styling, super/subscript, conservative
  unordered and ordered lists, monospaced code blocks, and simple table grids.
- Recover external link annotations, geometrically supported underline and
  highlight decoration, and conservative indented quotations in text mode.
- Infer strongly evidenced code languages and table-column alignment from text
  syntax and stable visual edges.
- Preserve obvious multi-part vector figures as cropped local PNG assets with
  alternative text derived only from their visible labels.
- Place embedded raster figures in document order, associate explicit nearby
  figure and table captions, and suppress repeated page furniture.
- Recover strong two-column reading order, internal page links, rotated text,
  and numeric superscript footnotes when their geometric evidence is complete.
- Extend strong-gutter reading order to three columns, join multiline footnote
  definitions, reuse identical raster assets across placements, anchor internal
  destinations without headings, and merge repeated table continuations across
  page breaks.
- Pair uniquely numbered footnotes across page boundaries and recover bordered
  table row/column spans only when enclosing cell geometry proves the grid.
- Supply PDF link destinations to hybrid extraction and strengthen visual
  guidance for code indentation, decoration, quotations, and diagrams.
- Reconcile hybrid repairs against deterministic text-mode output: wording
  changes are rejected, code repairs may change whitespace only, existing table
  alignment and asset references win, and semantic diagrams require confident
  bounding-box provenance.
- Preserve and remap deterministic and visual provenance through accepted hybrid
  structural repairs, and publish inference diagnostics separately from errors.
- Add a generated seven-document PDF regression corpus with hand-checked Carve
  answer keys and a repeatable 100-page performance profile.
- Drop internal links whose destination is outside the selected page range
  instead of emitting a dangling generated anchor.
- Keep hybrid baseline prompts within their stated byte budget even with large
  PDF metadata, and cache provider responses only after the reconciled document
  passes validation.
- Delimit multi-page cache keys, make concurrent cache writes collision-safe,
  and validate conversion modes, thresholds, portable IDs, language tokens,
  unique anchors, controls, and finite provenance numbers.

### Output

- Escape literal block-opening punctuation before it can become unintended
  Carve headings, lists, quotes, containers, tables, or thematic breaks.
- Emit canonical no-space code-fence info strings and padded table header cells,
  and leave single percentage signs unescaped while protecting `%%` comments.
- Emit native Carve table-alignment markers from the extraction model.
- Bind a figure id to the image it names. The attribute was written one space
  away, which detaches it: the braces became literal text, the id became a
  `#word` tag, and the caption line never bound, so a figure with an id
  rendered as none of those things.
- Keep a link or asset path whose URL holds a parenthesis. Only the closing one
  was encoded, which unbalanced a pair the destination scan already handled and
  dropped the whole link to literal text.
- Percent-encode other unsafe link and asset-destination characters at the
  writer boundary so provider-controlled values cannot open new Carve lines.
- Resolve a bare `--carve-command carve` through `PATH` and run official checks
  through a closed temporary file so validation also works on Windows.

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
