"""Generate a self-contained, inert HTML review report."""

from __future__ import annotations

import html
import json
from pathlib import Path

from .model import Document, document_to_json


def write_review(path: Path, *, source: str, document: Document, input_name: str) -> None:
    """Write escaped source, extraction JSON, and provenance for human review."""
    payload = json.dumps(document_to_json(document), ensure_ascii=False, indent=2)
    warnings = sum(len(item.warnings) for item in document.provenance)
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Carve conversion review</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:1rem;border-radius:.4rem}}
.summary{{display:flex;gap:2rem;flex-wrap:wrap}} details{{margin:1rem 0}}
</style></head><body>
<h1>Conversion review</h1>
<p>Input: <code>{html.escape(input_name)}</code></p>
<div class="summary"><span>Blocks: {len(document.blocks)}</span>
<span>Located blocks: {len(document.provenance)}</span><span>Warnings: {warnings}</span></div>
<details open><summary>Carve source</summary><pre>{html.escape(source)}</pre></details>
<details><summary>Validated extraction JSON</summary><pre>{html.escape(payload)}</pre></details>
</body></html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
