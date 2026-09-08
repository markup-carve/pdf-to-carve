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

## Confidence annotations

Use `--annotate-confidence` to append a provenance-comment index keyed by block
number:

```text
%% pdf-to-carve block=4 page=2 confidence=0.720 warnings=1
```

Keeping the index at the end prevents comments from splitting adjacent lists or
other blocks whose meaning depends on adjacency. Comments include no evidence
text and do not change rendered output. They are
opt-in because confidence is review metadata, not document content. A missing
provider score is emitted as `confidence=unknown`; it must not be treated as
high confidence. A block with no provenance is emitted with both page and
confidence set to `unknown`.

## Interactive correction

Save extraction JSON, then review uncertain blocks locally. The default queue
contains provenance-linked blocks with confidence below `0.85`, missing
confidence, or warnings:

```bash
pdf-to-carve extraction.json --from-json --correct \
  --save-json corrected.json --annotate-confidence -o corrected.crv
```

For each queued block, Enter leaves it unchanged and a one-line replacement
JSON object updates the block. Invalid JSON and
invalid model shapes are rejected and prompted again; output is serialized only
from the fully validated document. Use `--confidence-threshold` to tune the
queue. The original extraction file is never overwritten unless it is also
named explicitly as `--save-json`.

Correction never changes the provider's confidence. Corrected blocks carry a
machine-readable warning in JSON and annotations use `corrected` plus
`original-confidence`, making clear that the score describes the provider's
original extraction. A human decision and a model probability are different
facts; retain separate review records when an auditable approval trail is
required.
