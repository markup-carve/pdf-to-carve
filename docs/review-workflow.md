# Review workflow

Conversion is designed to produce evidence that can be inspected before publishing.
For a complex PDF, retain three artifacts:

```bash
pdf-to-carve input.pdf --mode hybrid -o output.crv \
  --save-json output.crv.json --review-html review.html \
  --assets-dir assets --cache-dir .cache/pdf-to-carve \
  --carve-command carve
```

Review warnings and low-confidence provenance first, then tables, equations,
diagrams, reading order, and repeated headers or footers. Compare the source PDF
with the generated Carve, edit the saved JSON when the extraction is wrong, and
replay it with `--from-json`. This separates extraction corrections from syntax.

The HTML report is static and self-contained. Untrusted document text and generated
source are HTML-escaped; it loads no scripts, fonts, or remote resources. It is a
review aid, not proof that the conversion is correct.

Cache entries contain provider output and can include the full document text. Keep
the cache outside version control, restrict access appropriately, and remove it
according to the document's retention policy.
