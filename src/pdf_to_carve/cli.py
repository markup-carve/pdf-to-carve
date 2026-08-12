"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .model import document_to_json
from .pipeline import ConversionOptions, convert, convert_json
from .review import write_review


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert PDF or image documents to Carve")
    parser.add_argument("input", type=Path, help="PDF, image, or extraction JSON")
    parser.add_argument("-o", "--output", type=Path, help="output .crv path (default: stdout)")
    parser.add_argument("--mode", choices=("auto", "text", "vision", "hybrid"), default="auto")
    parser.add_argument("--from-json", action="store_true", help="serialize saved extraction JSON")
    parser.add_argument("--save-json", type=Path, help="save the validated extraction model")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int)
    parser.add_argument("--model", help="provider model (defaults: gpt-4o-mini; sonnet for Claude)")
    parser.add_argument(
        "--provider",
        choices=("openai", "codex-cli", "claude-cli"),
        default="openai",
        help="vision provider",
    )
    parser.add_argument(
        "--pdf-backend",
        choices=("pdfium", "pymupdf"),
        default="pdfium",
        help="PDF engine (default: permissively licensed PDFium)",
    )
    parser.add_argument("--api-key", help="OpenAI provider API key; prefer OPENAI_API_KEY")
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--text-threshold", type=float, default=80.0)
    parser.add_argument("--retries", type=int, default=3, help="transient vision request attempts")
    parser.add_argument("--carve-command", help="official carve CLI used for fmt/lint verification")
    parser.add_argument("--dpi", type=int, default=180, help="vision raster DPI (72-400)")
    parser.add_argument("--max-pages", type=int, default=20, help="vision request safety limit")
    parser.add_argument("--cache-dir", type=Path, help="content-addressed response cache")
    parser.add_argument("--no-cache", action="store_true", help="bypass the configured cache")
    parser.add_argument("--assets-dir", type=Path, help="extract embedded raster assets")
    parser.add_argument("--max-input-mb", type=int, default=100, help="input-size safety limit")
    parser.add_argument("--review-html", type=Path, help="write an escaped local review report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.from_json:
            result = convert_json(args.input, args.carve_command)
        else:
            result = convert(
                args.input,
                ConversionOptions(
                    mode=args.mode,
                    start_page=args.start_page,
                    end_page=args.end_page,
                    model=args.model,
                    api_key=args.api_key,
                    base_url=args.base_url,
                    text_threshold=args.text_threshold,
                    retries=args.retries,
                    carve_command=args.carve_command,
                    dpi=args.dpi,
                    max_pages=args.max_pages,
                    cache_dir=args.cache_dir,
                    use_cache=not args.no_cache,
                    assets_dir=args.assets_dir,
                    max_input_mb=args.max_input_mb,
                    provider=args.provider,
                    pdf_backend=args.pdf_backend,
                ),
            )
        if args.save_json:
            args.save_json.write_text(
                json.dumps(document_to_json(result.document), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if args.output:
            args.output.write_text(result.source, encoding="utf-8")
        else:
            sys.stdout.write(result.source)
        if args.review_html:
            write_review(
                args.review_html,
                source=result.source,
                document=result.document,
                input_name=args.input.name,
            )
        print(
            f"pdf-to-carve: mode={result.mode}, blocks={len(result.document.blocks)}",
            file=sys.stderr,
        )
        for diagnostic in result.diagnostics:
            print(f"pdf-to-carve: {diagnostic}", file=sys.stderr)
        return 2 if result.diagnostics else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"pdf-to-carve: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
