# Privacy and security

Text mode is local: it reads the PDF with PDFium by default and makes no network request.
Vision and hybrid modes send rendered pages to the configured API endpoint; hybrid
also sends bounded extracted text and coordinates. Check the provider's retention,
training, regional-processing, and access policies before using sensitive material.
The optional `codex-cli` provider also sends these inputs to the Codex service using
the CLI's existing authentication; “CLI” does not mean offline or local inference.

Document content is untrusted data. The provider instruction explicitly forbids
following instructions found inside a document, the returned JSON is strictly
validated, and the deterministic writer owns Carve escaping. These controls reduce
prompt-injection and syntax-injection risk but cannot guarantee extraction accuracy.

Operational safeguards include:

- a default 100 MiB input limit, 20-page request limit, and bounded raster DPI;
- a 10 MiB response limit;
- retries only for transient network, rate-limit, and server failures;
- deterministic content-addressed caching only when a cache directory is requested;
- deduplicated, deterministic filenames for extracted embedded images;
- HTML escaping in local review reports.

API keys are read from `OPENAI_API_KEY` or supplied for the current invocation.
Do not commit keys, cache content, saved extraction JSON, source PDFs, or review
reports unless they are intentionally public. Always inspect output before it is
published or used in a consequential workflow.
