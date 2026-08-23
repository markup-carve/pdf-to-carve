"""Conversion orchestration with explicit deterministic and vision paths."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .cache import JsonCache, cache_key
from .extract import extract_text_pdf as pymupdf_extract_text
from .extract import text_coverage as pymupdf_text_coverage
from .layout import _pymupdf, evidence_prompt
from .layout import extract_embedded_images as pymupdf_extract_images
from .layout import positioned_text as pymupdf_positioned_text
from .model import Document
from .pdfium_backend import extract_embedded_images as pdfium_extract_images
from .pdfium_backend import extract_text_pdf as pdfium_extract_text
from .pdfium_backend import positioned_text as pdfium_positioned_text
from .pdfium_backend import render_pages as pdfium_render_pages
from .pdfium_backend import text_coverage as pdfium_text_coverage
from .reconcile import reconcile_hybrid
from .serialize import to_carve
from .vision import (
    SYSTEM_PROMPT,
    transcribe_images,
    transcribe_images_claude,
    transcribe_images_codex,
)


@dataclass(frozen=True)
class ConversionOptions:
    mode: Literal["auto", "text", "vision", "hybrid"] = "auto"
    start_page: int = 1
    end_page: int | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    text_threshold: float = 80.0
    retries: int = 3
    carve_command: str | None = None
    dpi: int = 180
    max_pages: int = 20
    cache_dir: Path | None = None
    use_cache: bool = True
    assets_dir: Path | None = None
    max_input_mb: int = 100
    provider: Literal["openai", "codex-cli", "claude-cli"] = "openai"
    pdf_backend: Literal["pdfium", "pymupdf"] = "pdfium"


@dataclass(frozen=True)
class ConversionResult:
    source: str
    document: Document
    mode: str
    diagnostics: tuple[str, ...] = ()


def _baseline_prompt(document: dict[str, Any], max_chars: int = 60_000) -> str:
    """Return valid, bounded baseline JSON for visual repair guidance."""
    envelope = {
        key: value for key, value in document.items() if key not in {"blocks", "provenance"}
    }
    envelope["blocks"] = []
    for block in document.get("blocks", []):
        candidate = {**envelope, "blocks": [*envelope["blocks"], block]}
        encoded = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > max_chars:
            envelope["truncated"] = True
            break
        envelope = candidate
    return json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))


def _render_pages(
    path: Path, directory: Path, start: int, end: int | None, *, dpi: int, max_pages: int
) -> list[Path]:
    if path.suffix.lower() != ".pdf":
        return [path]
    pymupdf = _pymupdf()
    doc = pymupdf.open(path)
    try:
        last = doc.page_count if end is None else min(end, doc.page_count)
        if start < 1 or start > last:
            raise ValueError(f"invalid page range {start}-{last} for {doc.page_count} pages")
        if last - start + 1 > max_pages:
            raise ValueError(f"selected range has {last - start + 1} pages; maximum is {max_pages}")
        result = []
        for number in range(start - 1, last):
            target = directory / f"page-{number + 1}.png"
            doc[number].get_pixmap(dpi=dpi, alpha=False).save(target)
            result.append(target)
        return result
    finally:
        doc.close()


def _official_check(source: str, command: str) -> tuple[str, ...]:
    executable = str(Path(command).expanduser().resolve())
    with tempfile.NamedTemporaryFile("w", suffix=".crv", encoding="utf-8") as handle:
        handle.write(source)
        handle.flush()
        formatted = subprocess.run(
            [executable, "fmt", "--check", handle.name],
            capture_output=True,
            text=True,
            check=False,
        )
        linted = subprocess.run(
            [executable, "lint", handle.name], capture_output=True, text=True, check=False
        )
    messages = []
    if formatted.returncode:
        messages.append(
            (formatted.stderr or formatted.stdout).strip() or "carve fmt rejected output"
        )
    if linted.returncode:
        messages.append((linted.stderr or linted.stdout).strip() or "carve lint rejected output")
    return tuple(messages)


def convert(path: Path, options: ConversionOptions | None = None) -> ConversionResult:
    if options is None:
        options = ConversionOptions()
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if options.max_input_mb < 1:
        raise ValueError("max_input_mb must be positive")
    if path.stat().st_size > options.max_input_mb * 1024 * 1024:
        raise ValueError(f"input exceeds the {options.max_input_mb} MiB safety limit")
    is_pdf = path.suffix.lower() == ".pdf"
    if options.provider not in ("openai", "codex-cli", "claude-cli"):
        raise ValueError(f"unsupported vision provider: {options.provider}")
    model = options.model or ("sonnet" if options.provider == "claude-cli" else "gpt-4o-mini")
    if options.pdf_backend not in ("pdfium", "pymupdf"):
        raise ValueError(f"unsupported PDF backend: {options.pdf_backend}")
    extract_text = pdfium_extract_text if options.pdf_backend == "pdfium" else pymupdf_extract_text
    coverage = pdfium_text_coverage if options.pdf_backend == "pdfium" else pymupdf_text_coverage
    positioned = (
        pdfium_positioned_text if options.pdf_backend == "pdfium" else pymupdf_positioned_text
    )
    extract_images = (
        pdfium_extract_images if options.pdf_backend == "pdfium" else pymupdf_extract_images
    )
    selected = options.mode
    if selected == "auto":
        selected = (
            "text"
            if is_pdf
            and coverage(path, options.start_page, options.end_page) >= options.text_threshold
            else "vision"
        )
    if selected == "text":
        if not is_pdf:
            raise ValueError("text mode supports PDF input only")
        raw = (
            pdfium_extract_text(path, options.start_page, options.end_page, options.assets_dir)
            if options.pdf_backend == "pdfium"
            else extract_text(path, options.start_page, options.end_page)
        )
    else:
        if options.dpi < 72 or options.dpi > 400:
            raise ValueError("dpi must be between 72 and 400")
        if options.max_pages < 1:
            raise ValueError("max_pages must be positive")
        with tempfile.TemporaryDirectory(prefix="pdf-to-carve-") as temp:
            images = (
                pdfium_render_pages(
                    path,
                    Path(temp),
                    options.start_page,
                    options.end_page,
                    dpi=options.dpi,
                    max_pages=options.max_pages,
                )
                if is_pdf and options.pdf_backend == "pdfium"
                else _render_pages(
                    path,
                    Path(temp),
                    options.start_page,
                    options.end_page,
                    dpi=options.dpi,
                    max_pages=options.max_pages,
                )
            )
            context = None
            baseline = None
            if selected == "hybrid":
                if not is_pdf:
                    raise ValueError("hybrid mode supports PDF input only")
                baseline = (
                    pdfium_extract_text(
                        path, options.start_page, options.end_page, options.assets_dir
                    )
                    if options.pdf_backend == "pdfium"
                    else extract_text(path, options.start_page, options.end_page)
                )
                context = evidence_prompt(positioned(path, options.start_page, options.end_page))
                baseline_json = _baseline_prompt(baseline)
                context += f"\nTRUSTED TEXT-MODE BASELINE JSON:\n{baseline_json}"
                context += (
                    "\nReturn a visually repaired document, preserving baseline wording exactly. "
                    "Only whitespace in code may change. Include exactly one provenance entry per "
                    "repaired or visually reconstructed block, using a defensible page, bbox, "
                    "confidence, and warnings."
                )
            cache = JsonCache(options.cache_dir) if options.cache_dir else None
            key = cache_key(
                files=images,
                model=f"{options.provider}:{model}",
                prompt=f"{SYSTEM_PROMPT}\n{context or ''}",
            )
            raw = cache.get(key) if cache and options.use_cache else None
            if raw is None:
                if options.provider == "codex-cli":
                    raw = transcribe_images_codex(images, model=model, context=context)
                elif options.provider == "claude-cli":
                    raw = transcribe_images_claude(images, model=model, context=context)
                else:
                    raw = transcribe_images(
                        images,
                        model=model,
                        api_key=options.api_key,
                        base_url=options.base_url,
                        retries=options.retries,
                        context=context,
                    )
                if cache and options.use_cache:
                    cache.put(key, raw)
            if selected == "hybrid" and baseline is not None:
                raw = reconcile_hybrid(baseline, raw)
    if options.assets_dir and is_pdf:
        extract_images(path, options.assets_dir)
    document = Document.from_json(raw)
    source = to_carve(document)
    diagnostics = _official_check(source, options.carve_command) if options.carve_command else ()
    return ConversionResult(source, document, selected, diagnostics)


def convert_json(path: Path, carve_command: str | None = None) -> ConversionResult:
    document = Document.from_json(json.loads(path.read_text(encoding="utf-8")))
    source = to_carve(document)
    diagnostics = _official_check(source, carve_command) if carve_command else ()
    return ConversionResult(source, document, "json", diagnostics)
