# Privacy and security

Text mode is local: it reads the PDF with PDFium by default and makes no network request.
Vision and hybrid modes send rendered pages to the configured API endpoint; hybrid
also sends bounded extracted text, coordinates, and a bounded deterministic baseline. Check the provider's retention,
training, regional-processing, and access policies before using sensitive material.
The optional `codex-cli` and `claude-cli` providers also send these inputs to their
respective remote services using each CLI's existing authentication; “CLI” does
not mean offline or local inference. The Claude integration copies rendered pages
into a temporary directory, grants only that directory to the `Read` tool, disables
project customizations and session persistence, and rejects permission denials.

Document content is untrusted data. The provider instruction explicitly forbids
following instructions found inside a document, the returned JSON is strictly
validated, hybrid wording is reconciled against local text evidence, and the
deterministic writer owns Carve escaping. These controls reduce
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

## Redacting before cloud vision

Redaction must happen **before rendering or upload**. Drawing a black rectangle
over text in a PDF is not enough: the underlying text layer, annotations,
attachments, metadata, and earlier revisions may remain extractable. Make a
sanitized derivative and keep the original outside the conversion workspace.

1. Classify the document and identify personal data, credentials, account
   numbers, signatures, faces, barcodes, marginalia, metadata, and attachments.
2. Use a redaction tool that removes underlying objects, not visual masking.
   Remove document metadata, embedded files, JavaScript, comments, and hidden
   layers as separate steps.
3. Export or print to a new flattened PDF, then independently inspect both its
   rendered pages and extracted text. Search for every redacted value and a
   distinctive substring of it.
4. Run `pdf-to-carve` on the sanitized derivative with the smallest necessary
   page range and DPI. Prefer local `--mode text` whenever it is sufficient.
5. Treat page images, hybrid text evidence, provider responses, caches,
   extraction JSON, logs, and review files as copies of the source for access
   control and retention purposes.
6. Record provider, model, endpoint, region, purpose, approval, pages sent,
   deletion date, and the hash of the sanitized derivative. Never record the
   removed values themselves in that audit entry.
7. Delete remote jobs where the provider supports it and remove local temporary
   artifacts and caches on the approved schedule. Verify deletion rather than
   assuming process exit removed a configured cache.

For regulated or confidential material, obtain the required organizational and
legal approval before upload. Confirm the provider contract and current
retention, training, subprocessors, regional processing, incident-response, and
data-subject-request terms; product defaults and consumer-account terms are not
a substitute. If those conditions cannot be verified, do not use cloud vision.

Redaction can remove context needed for correct reading order or table recovery.
Re-check the sanitized derivative as a document, mark intentional gaps in the
review record, and never use synthetic replacement text that could be mistaken
for extracted fact.
