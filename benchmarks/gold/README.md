# Deterministic gold set

This release gate measures born-digital text extraction against seven
hand-checked Carve answer keys. Cases are stratified by their primary document
class and additionally tagged with layout features in `manifest.json`.

Verify the reviewed inputs and recompute both published artifacts:

```bash
uv run python benchmarks/gold/score.py --output benchmarks/gold/results.json \
  --report benchmarks/gold/REPORT.md
uv run pytest tests/test_gold_benchmark.py tests/test_pdf_corpus.py
```

The manifest pins both input and answer-key SHA-256 digests. The scorer refuses
to run after either changes until a reviewer deliberately updates the manifest.
`tests/pdf_corpus/generate.py` is the reviewable drawing source, but PDF container
bytes can vary across PyMuPDF versions; the checked-in, hash-pinned PDFs are the
benchmark inputs. Scoring uses local PDFium text mode only: no network service,
model, or mutable remote fixture participates.

This is a regression gold set, not a claim about arbitrary PDFs. It is small,
synthetic, and intentionally rich in previously failing structures. Scores must
be reported with its seven-document size and class distribution. Its answer
keys are the same pinned, hand-checked snapshots used by the release regression
tests, so zero error demonstrates determinism against known cases rather than an
independent estimate of population accuracy.
