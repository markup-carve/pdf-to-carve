# Development

## Setup and maintenance

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=pdf_to_carve --cov-report=term-missing
uv run python benchmarks/gold/score.py --output benchmarks/gold/results.json \
  --report benchmarks/gold/REPORT.md
uv build
```
