# Deterministic text-mode performance, 23 August 2026

The repeatable profile generates a 100-page born-digital PDF. Every page has a
repeated header and changing page number, a heading, 24 text lines, and a
three-row table. It then runs the full text conversion five times in one Python
process.

```bash
uv run python benchmarks/profile_text.py --pages 100 --runs 5
```

Measured result:

| Pages | Output blocks | Median | Range | Process peak RSS |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 2,499 | 1.5759 s | 1.5296 to 1.6924 s | 77.7 MiB |

Environment: Linux 7.0.0-29-generic, Python 3.12.3, AMD Ryzen 9 PRO 7940HS,
16 logical CPUs. The extractor is single-process and does not use the network.

This synthetic workload measures positioned text, repeated-furniture analysis,
tables, document validation, provenance, and Carve serialization. It does not
represent scanned PDFs, asset rendering, provider latency, or arbitrary
real-world complexity. Run the checked-in script on deployment hardware rather
than treating this observation as a universal benchmark.
