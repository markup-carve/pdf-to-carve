# PDF backend licensing options

The `pdf-to-carve` source code is MIT licensed. The complete installed stack has
an additional consideration: its current PDF backend, PyMuPDF, is offered under
the GNU AGPL v3 or a commercial Artifex license. This note is an engineering
decision record, not legal advice.

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

### 3. Make PyMuPDF an optional backend

Move PyMuPDF behind an installation extra and define a backend interface. The
base package could remain dependency-light and permissively deployable, while
users explicitly choosing PyMuPDF would accept its terms or provide a commercial
license. This is useful only if the base installation has another functional PDF
backend; making the dependency optional without a replacement would merely move
the failure to runtime.

### 4. Migrate to a permissive backend

Implement text extraction and rendering with a permissively licensed PDFium
binding or another vetted backend. This offers the cleanest default dependency
story, but it must pass parity tests for text coordinates, metadata, page-range
handling, rasterization, embedded-image extraction, malformed files, and the
known-ground-truth PDF corpus before replacing PyMuPDF.

## Recommendation

Use option 3 as the transition architecture and option 4 as the target:

1. Introduce a narrow PDF-backend protocol.
2. Preserve PyMuPDF as the tested compatibility backend.
3. Add a permissive backend behind its own extra.
4. Run both through identical unit, fuzz, and complex-PDF fidelity tests.
5. Change the default only after the permissive backend reaches quality parity.

Until that work is complete, keep PyMuPDF explicit in installation and security
documentation. Do not claim that the entire dependency stack is MIT licensed.

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
- [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html)
- [Artifex licensing](https://artifex.com/licensing/)
