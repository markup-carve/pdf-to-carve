# Security policy

Please report vulnerabilities privately through GitHub Security Advisories.
Do not include API keys, private documents, or provider responses in an issue.

PDFs, images, extracted strings, URLs, and model responses are untrusted input.
The converter never executes document content. Model requests send selected
page images to the configured endpoint; use text mode or `--from-json` when a
document must not leave the local machine.

