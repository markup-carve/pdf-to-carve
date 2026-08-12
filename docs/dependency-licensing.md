# PDF backend licensing options

The `pdf-to-carve` source code is MIT licensed. Its default PDF stack uses
`pypdfium2`, which offers BSD-3-Clause or Apache-2.0 terms, and PDFium, whose
upstream license is BSD-style. This note is an engineering decision record, not
legal advice.

The locally installed benchmark tools are not dependencies. They live outside
the repository and are not included in source archives, wheels, or releases.
Removing or export-ignoring benchmark files therefore would not change the
runtime licensing question.

## Available choices

### 1. Keep the current backend under AGPL terms

Keep PyMuPDF required and document that deployments must comply with its AGPL
terms. This preserves current behavior and requires no engineering migration.
It may be unsuitable for consumers that cannot meet the applicable source-code
and network-use obligations.

### 2. Use a commercial PyMuPDF license

Keep the current implementation and obtain an appropriate commercial license
from Artifex for deployments that do not use the AGPL option. This has the least
technical risk, but introduces procurement, cost, and license-management work.

### 3. Make PyMuPDF an optional backend (implemented)

PyMuPDF is available only through the `pymupdf` extra and explicit
`--pdf-backend pymupdf` selection. Users choosing it must assess its AGPL terms
or provide a commercial license. The base installation does not import or need
PyMuPDF.

### 4. Migrate to a permissive backend (implemented as the default)

PDFium now implements text extraction, text coordinates, metadata, page-range
handling, rasterization, and embedded-image extraction. PyMuPDF remains an
explicit compatibility and rollback option.

## Measured migration result

The known-ground-truth complex-PDF corpus produced these local averages. Scores
range from 0 to 1; higher is better. Runtime and memory cover text-mode CLI
conversion on the same machine.

| Measure | PDFium default | PyMuPDF compatibility |
| --- | ---: | ---: |
| Text character fidelity | 0.818 | 0.828 |
| Text word fidelity | 0.790 | 0.813 |
| Hybrid character fidelity | 0.939 | 0.958 |
| Hybrid word fidelity | 0.914 | 0.921 |
| Hybrid structure fidelity | 0.961 | 0.961 |
| Text-mode time per document | 0.08–0.09 s | 0.18 s |
| Text-mode peak memory | 29–30 MiB | 65–67 MiB |

At 180 DPI, page rasterizations had 0.9967–0.9996 pixel similarity. Hybrid
vision results are nondeterministic and should be treated as samples, while the
text and raster measurements are deterministic for the tested versions.

The default is therefore PDFium: it is materially faster and smaller, preserves
structure in the hybrid path, and has near-parity deterministic fidelity. Keep
the compatibility extra for consumers that require the final few points of text
fidelity. Do not describe third-party dependencies as MIT merely because this
project's own source is MIT.

## Decision checklist

- Intended distribution: internal, hosted service, open-source application, or
  proprietary product
- Whether AGPL obligations are acceptable for that distribution
- Commercial-license cost and operational ownership
- Required fidelity for coordinates, tables, images, scans, and rendering
- Supported operating systems and binary-wheel availability
- Security maintenance and malformed-PDF handling
- Benchmark parity and migration rollback plan

Primary references:

- [PyMuPDF licensing](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
- [pypdfium2 licensing](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing)
- [PDFium license](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/LICENSE)
- [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html)
- [Artifex licensing](https://artifex.com/licensing/)
