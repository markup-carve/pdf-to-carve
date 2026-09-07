# Born-digital extraction accuracy

- Mode: deterministic PDFium text extraction
- Gold set: 7 generated, hand-checked documents

## Results

| Document class | Documents | Exact | Character error rate | Word error rate |
| --- | ---: | ---: | ---: | ---: |
| Complex tables | 1 | 1/1 | 0.00% | 0.00% |
| Mixed layout | 1 | 1/1 | 0.00% | 0.00% |
| Multi-column | 2 | 2/2 | 0.00% | 0.00% |
| References | 1 | 1/1 | 0.00% | 0.00% |
| Repeated furniture | 1 | 1/1 | 0.00% | 0.00% |
| Visual assets | 1 | 1/1 | 0.00% | 0.00% |
| **Overall** | **7** | **7/7** | **0.00%** | **0.00%** |

Character edits: 0 insertions, 0 deletions, and 0 substitutions. Word edits:
0 insertions, 0 deletions, and 0 substitutions.
Document accuracy requires byte-for-byte equality with the complete Carve
answer key; it is not a text-only comparison.

Character error rate is minimum Levenshtein character edits divided by gold
characters. Word error rate uses whitespace-delimited tokens. The published
machine-readable counts, including every case and error type, are in
`results.json`.

## Interpretation

The result establishes deterministic regression accuracy for these fixtures.
The answer keys are the same pinned, hand-checked snapshots used by the release
tests, so a green release gate necessarily reports zero error here. The measures
are a determinism check, not an independent accuracy estimate.
It does not estimate performance on natural document populations, scans, or
cloud-vision providers. The set contains only 7 small generated documents;
most strata have one member. Its purpose is to make known layout behavior
reproducible and failures measurable while a larger, independently sourced set
is assembled.
