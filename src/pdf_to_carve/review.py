"""Generate local HTML review artifacts."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from .model import HUMAN_CORRECTED_WARNING, Document, document_to_json


def _script_json(value: object) -> str:
    """Serialize data for an HTML raw-text script element without ending it."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def validate_source_pdf(path: Path) -> None:
    """Reject a missing, misnamed, or non-PDF correction preview."""
    if not path.is_file():
        raise ValueError(f"source PDF does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("correction workspace source must be a PDF")
    with path.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise ValueError("correction workspace source does not have a PDF header")


def write_correction_workspace(
    path: Path,
    *,
    document: Document,
    input_name: str,
    source_pdf: Path | None = None,
) -> None:
    """Write an offline block editor with local resume and fixture export."""
    if source_pdf is not None:
        validate_source_pdf(source_pdf)
    raw = document_to_json(document)
    if not raw["blocks"]:
        raise ValueError("correction workspace requires at least one block")
    digest = hashlib.sha256(
        json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    config = {
        "document": raw,
        "inputName": input_name,
        "documentSha256": digest,
        "pdfUrl": source_pdf.resolve().as_uri() if source_pdf else None,
        "correctedWarning": HUMAN_CORRECTED_WARNING,
    }
    template = Path(__file__).with_name("workspace.html").read_text(encoding="utf-8")
    body = template.replace("__PDF_TO_CARVE_CONFIG__", _script_json(config))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def write_review(path: Path, *, source: str, document: Document, input_name: str) -> None:
    """Write escaped source, extraction JSON, and provenance for human review."""
    payload = json.dumps(document_to_json(document), ensure_ascii=False, indent=2)
    warnings = sum(
        warning != HUMAN_CORRECTED_WARNING
        for item in document.provenance
        for warning in item.warnings
    )
    corrected = sum(HUMAN_CORRECTED_WARNING in item.warnings for item in document.provenance)
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
<span>Located blocks: {len(document.provenance)}</span><span>Warnings: {warnings}</span>
<span>Corrected blocks: {corrected}</span></div>
<details open><summary>Carve source</summary><pre>{html.escape(source)}</pre></details>
<details><summary>Validated extraction JSON</summary><pre>{html.escape(payload)}</pre></details>
</body></html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
