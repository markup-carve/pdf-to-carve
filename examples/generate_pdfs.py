"""Regenerate the small, CC0 example PDFs committed in this directory."""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).parent


def _save(doc: pymupdf.Document, name: str) -> None:
    doc.set_metadata({"title": name, "author": "pdf-to-carve contributors"})
    doc.save(ROOT / name / "input.pdf", garbage=4, deflate=True, no_new_id=True)
    doc.close()


def scientific() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((45, 55), "Adaptive Signals", fontsize=20)
    page.insert_text((45, 82), "A compact two-column research example", fontsize=11)
    page.insert_text((45, 120), "1. Method", fontsize=15)
    left = (
        "We estimate the response from noisy observations.\n"
        "The objective combines fit and regularization:\n\n"
        "J(theta) = sum_i (y_i - f_theta(x_i))^2 + lambda ||theta||^2\n\n"
        "The optimum improved accuracy by 12.4%.[1]"
    )
    right = (
        "2. Results\n\n"
        "Condition       Accuracy     Samples\n"
        "Baseline        81.2%        240\n"
        "Adaptive        93.6%        240\n\n"
        "[1] Values are means over five seeded runs."
    )
    page.insert_textbox(pymupdf.Rect(45, 145, 285, 430), left, fontsize=10)
    page.insert_textbox(pymupdf.Rect(310, 120, 550, 430), right, fontsize=10)
    _save(doc, "scientific-paper")


def financial() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((45, 55), "Northwind Quarterly Summary", fontsize=20)
    page.insert_text((45, 88), "Revenue by region (EUR thousands)", fontsize=13)
    xs = [45, 205, 320, 435, 550]
    ys = [110, 140, 170, 200, 230]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    cells = [
        ("Region", "Q1", "Q2", "Change"),
        ("North", "1,240", "1,410", "+13.7%"),
        ("South", "980", "1,020", "+4.1%"),
        ("Total", "2,220", "2,430", "+9.5%"),
    ]
    for row, values in enumerate(cells):
        for column, value in enumerate(values):
            page.insert_text((xs[column] + 6, ys[row] + 20), value, fontsize=10)
    page.insert_text((45, 275), "Highlights", fontsize=15)
    page.insert_text((55, 302), "- Recurring revenue reached 68%.", fontsize=11)
    page.insert_text((55, 324), "- Operating margin increased to 17.2%.", fontsize=11)
    page.draw_rect(pymupdf.Rect(45, 360, 550, 425), color=(0.8, 0.45, 0), fill=(1, 0.96, 0.85))
    page.insert_text((58, 385), "Caution", fontsize=12)
    page.insert_text((58, 408), "Currency movements may affect the next quarter.", fontsize=10)
    _save(doc, "financial-report")


def editorial() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((45, 55), "Editorial Review", fontsize=20)
    page.insert_text((45, 95), "Draft sentence", fontsize=13)
    page.insert_text((45, 125), "The launch is scheduled for Tuesday.", fontsize=11)
    page.draw_line((45, 121), (218, 121), color=(0.8, 0, 0), width=1.2)
    page.insert_text((45, 165), "Revised sentence", fontsize=13)
    page.insert_text((45, 195), "The public preview is scheduled for Thursday.", fontsize=11)
    page.draw_rect(pymupdf.Rect(42, 178, 292, 202), color=(0, 0.55, 0), width=1)
    page.insert_text((45, 245), "Reviewer note", fontsize=13)
    page.draw_rect(pymupdf.Rect(45, 260, 520, 322), color=(0.15, 0.35, 0.8), fill=(0.9, 0.94, 1))
    page.insert_text((58, 285), "Confirm legal approval before publishing.", fontsize=11)
    page.insert_text((58, 307), "Keep both revisions in the audit trail.", fontsize=11)
    _save(doc, "editorial-review")


if __name__ == "__main__":
    scientific()
    financial()
    editorial()
