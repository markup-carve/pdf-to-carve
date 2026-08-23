"""Profile deterministic extraction on a generated, repeatable large PDF."""

from __future__ import annotations

import argparse
import json
import resource
import statistics
import tempfile
import time
from pathlib import Path

import pymupdf

from pdf_to_carve.pipeline import ConversionOptions, convert


def generate(path: Path, pages: int) -> None:
    document = pymupdf.open()
    for number in range(1, pages + 1):
        page = document.new_page(width=595, height=842)
        page.insert_text((40, 24), "Generated performance report", fontsize=8)
        page.insert_text((40, 65), f"Section {number}", fontsize=18, fontname="hebo")
        for line in range(24):
            page.insert_text(
                (40, 100 + line * 20),
                f"Page {number} line {line + 1} contains deterministic searchable document text.",
                fontsize=10,
            )
        for y, values in (
            (620, ("Region", "Value")),
            (640, ("North", "1,240")),
            (660, ("South", "980")),
        ):
            page.insert_text((40, y), values[0], fontsize=10)
            page.insert_text((420, y), values[1], fontsize=10)
        page.insert_text((280, 820), f"Page {number}", fontsize=8)
    document.save(path)
    document.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=100)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pdf-to-carve-profile-") as directory:
        pdf = Path(directory) / "large.pdf"
        generate(pdf, args.pages)
        durations = []
        block_count = 0
        for _ in range(args.runs):
            started = time.perf_counter()
            result = convert(pdf, ConversionOptions(mode="text"))
            durations.append(time.perf_counter() - started)
            block_count = len(result.document.blocks)
        print(
            json.dumps(
                {
                    "pages": args.pages,
                    "runs": args.runs,
                    "blocks": block_count,
                    "median_seconds": round(statistics.median(durations), 4),
                    "range_seconds": [round(min(durations), 4), round(max(durations), 4)],
                    "peak_rss_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1
                    ),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
