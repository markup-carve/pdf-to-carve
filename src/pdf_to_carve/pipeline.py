"""Conversion orchestration with explicit deterministic and vision paths."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf

from .extract import extract_text_pdf, text_coverage
from .model import Document
from .serialize import to_carve
from .vision import transcribe_images


@dataclass(frozen=True)
class ConversionOptions:
    mode: Literal["auto", "text", "vision"] = "auto"
    start_page: int = 1
    end_page: int | None = None
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    text_threshold: float = 80.0
    retries: int = 3
    carve_command: str | None = None


@dataclass(frozen=True)
class ConversionResult:
    source: str
    document: Document
    mode: str
    diagnostics: tuple[str, ...] = ()


def _render_pages(path: Path, directory: Path, start: int, end: int | None) -> list[Path]:
    if path.suffix.lower() != ".pdf":
        return [path]
    doc = pymupdf.open(path)
    try:
        last = doc.page_count if end is None else min(end, doc.page_count)
        if start < 1 or start > last:
            raise ValueError(f"invalid page range {start}-{last} for {doc.page_count} pages")
        result = []
        for number in range(start - 1, last):
            target = directory / f"page-{number + 1}.png"
            doc[number].get_pixmap(dpi=180, alpha=False).save(target)
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
    is_pdf = path.suffix.lower() == ".pdf"
    selected = options.mode
    if selected == "auto":
        selected = (
            "text"
            if is_pdf
            and text_coverage(path, options.start_page, options.end_page) >= options.text_threshold
            else "vision"
        )
    if selected == "text":
        if not is_pdf:
            raise ValueError("text mode supports PDF input only")
        raw = extract_text_pdf(path, options.start_page, options.end_page)
    else:
        with tempfile.TemporaryDirectory(prefix="pdf-to-carve-") as temp:
            images = _render_pages(path, Path(temp), options.start_page, options.end_page)
            raw = transcribe_images(
                images,
                model=options.model,
                api_key=options.api_key,
                base_url=options.base_url,
                retries=options.retries,
            )
    document = Document.from_json(raw)
    source = to_carve(document)
    diagnostics = _official_check(source, options.carve_command) if options.carve_command else ()
    return ConversionResult(source, document, selected, diagnostics)


def convert_json(path: Path, carve_command: str | None = None) -> ConversionResult:
    document = Document.from_json(json.loads(path.read_text(encoding="utf-8")))
    source = to_carve(document)
    diagnostics = _official_check(source, carve_command) if carve_command else ()
    return ConversionResult(source, document, "json", diagnostics)
