# Competitor benchmark — August 2026

This report is generated from the committed raw observations by `score.py`.
Higher fidelity and structural-recall scores are better. Completion is never folded
into a quality average. See [README.md](README.md) for method and limitations.

| Extractor | Version | Completed | Character | Word | Structure |
| --- | --- | ---: | ---: | ---: | ---: |
| Carve hybrid via Codex CLI | pdf-to-carve a23249a; gpt-5.6-sol low | 2/2 | 0.934 | 0.861 | 0.873 |
| Docling | 2.119.0 | 1/2 | 0.920 | 0.858 | 0.217 |
| Unstructured fast | 0.25.2 | 2/2 | 0.831 | 0.777 | n/a |
| Carve deterministic text | pdf-to-carve 4d28758; PyMuPDF backend | 2/2 | 0.827 | 0.772 | 0.105 |
| Microsoft MarkItDown | 0.1.7 | 2/2 | 0.819 | 0.746 | 0.170 |
| Marker | 2.0.0 | 2/2 | 0.806 | 0.812 | 0.384 |
| MinerU | 3.4.4 | 2/2 | 0.793 | 0.715 | 0.254 |
| PyMuPDF4LLM | 1.28.2 | 2/2 | 0.776 | 0.758 | 0.551 |
| MarkPDFdown | 1.1.2 at 4b38fd8f91bd5cd61181bd3c68bf025f6040115b; gpt-4o | 0/2 | n/a | n/a | n/a |

## Per-document evidence

| Extractor | Fixture | Status | Character | Word | Structural kinds |
| --- | --- | --- | ---: | ---: | ---: |
| Carve hybrid via Codex CLI | 02-showcase | complete | 0.95667 | 0.928571 | 21/23 |
| Carve hybrid via Codex CLI | 03-math-diagrams | complete | 0.912269 | 0.792541 | 5/6 |
| Docling | 02-showcase | complete | 0.920482 | 0.858086 | 5/23 |
| Docling | 03-math-diagrams | timeout | n/a | n/a | n/a |
| Unstructured fast | 02-showcase | complete | 0.86024 | 0.801303 | n/a |
| Unstructured fast | 03-math-diagrams | complete | 0.801084 | 0.753247 | n/a |
| Carve deterministic text | 02-showcase | complete | 0.86024 | 0.801303 | 1/23 |
| Carve deterministic text | 03-math-diagrams | complete | 0.79397 | 0.742857 | 1/6 |
| Microsoft MarkItDown | 02-showcase | complete | 0.844837 | 0.782353 | 4/23 |
| Microsoft MarkItDown | 03-math-diagrams | complete | 0.793077 | 0.709046 | 1/6 |
| Marker | 02-showcase | complete | 0.899345 | 0.886667 | 10/23 |
| Marker | 03-math-diagrams | complete | 0.713471 | 0.738095 | 2/6 |
| MinerU | 02-showcase | complete | 0.845638 | 0.745645 | 4/23 |
| MinerU | 03-math-diagrams | complete | 0.740364 | 0.684492 | 2/6 |
| PyMuPDF4LLM | 02-showcase | complete | 0.796117 | 0.769231 | 10/23 |
| PyMuPDF4LLM | 03-math-diagrams | complete | 0.755396 | 0.747368 | 4/6 |
| MarkPDFdown | 02-showcase | provider_error_empty_output_exit_0 | n/a | n/a | n/a |
| MarkPDFdown | 03-math-diagrams | not_attempted_after_shared_provider_exhaustion | n/a | n/a | n/a |

## Operational observations

Times and peak RSS are sequential local samples, not normalized throughput.
Batch-only measurements and timeout details remain in `runs.json`.

| Extractor | Per-document seconds | Peak RSS MiB |
| --- | ---: | ---: |
| Carve hybrid via Codex CLI | 48.84, 29.88 | 184.5, 185.5 |
| Docling | n/a | n/a |
| Unstructured fast | n/a | n/a |
| Carve deterministic text | 0.38, 0.31 | 57.0, 60.8 |
| Microsoft MarkItDown | 1.54, 1.35 | 144.6, 146.4 |
| Marker | 78.43, 60.37 | 969.2, 977.5 |
| MinerU | 64.48, 28.20 | 2347.4, 2161.2 |
| PyMuPDF4LLM | 1.29, 1.08 | 147.9, 148.8 |
| MarkPDFdown | 7.68 | 340.5 |

## Reading the result

The Carve hybrid sample leads both text-fidelity means and structural-kind recall
on this corpus. Marker has the strongest structural-kind recall among completed
third-party runs, while Docling has a strong single-document text score but timed
out before completing the corpus. Plain-text-only output has no structural score.

One vision competitor is listed but unscored: the available provider account was
credit-exhausted. The tool logged the page failure, returned exit status zero, and
created an empty output. The sanitized observation is committed under `raw/`.
That is an operational finding, not a fidelity comparison.

These independently recomputed scores intentionally supersede the earlier PR-summary
table, whose exact scoring script and intermediate normalization were not retained.
No claim should rely on that older table when this auditable report is available.
