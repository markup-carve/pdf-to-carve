"""Generate the deterministic PDF regression corpus from reviewable drawing code."""

from pathlib import Path

import pymupdf

ROOT = Path(__file__).parent


def save(name: str, draw) -> None:
    document = pymupdf.open()
    draw(document)
    document.save(ROOT / f"{name}.pdf")
    document.close()


def columns(document) -> None:
    page = document.new_page(width=500, height=500)
    page.insert_text((20, 35), "Column study", fontsize=20, fontname="hebo")
    for y, left, right in (
        (90, "Left one carries enough text for a column.", "Right one carries enough text too."),
        (102, "Left two remains in reading order.", "Right two follows its own first line."),
        (114, "Left three closes the first column.", "Right three closes the second column."),
    ):
        page.insert_text((20, y), left, fontsize=9)
        page.insert_text((270, y), right, fontsize=9)


def furniture(document) -> None:
    for number in range(1, 4):
        page = document.new_page(width=400, height=500)
        page.insert_text((20, 24), "ACME confidential", fontsize=8)
        page.insert_text((20, 90), f"Page-specific paragraph {number}.", fontsize=11)
        page.insert_text((175, 485), f"Page {number}", fontsize=8)


def three_columns(document) -> None:
    page = document.new_page(width=600, height=400)
    page.insert_text((20, 35), "Three column digest", fontsize=20, fontname="hebo")
    for y, values in (
        (
            90,
            (
                "First column begins with text.",
                "Second column begins with text.",
                "Third column begins with text.",
            ),
        ),
        (
            102,
            (
                "First column then continues.",
                "Second column then continues.",
                "Third column then continues.",
            ),
        ),
    ):
        for x, value in zip((20, 220, 420), values, strict=True):
            page.insert_text((x, y), value, fontsize=9)


def links_footnotes(document) -> None:
    first = document.new_page(width=400, height=400)
    first.insert_text((20, 35), "Overview", fontsize=20, fontname="hebo")
    first.insert_text((20, 85), "Read details", fontsize=10)
    first.insert_text((20, 125), "A supported claim", fontsize=10)
    first.insert_text((110, 121), "1", fontsize=7)
    first.insert_text((20, 340), "1 First footnote line", fontsize=8)
    first.insert_text((32, 352), "continues on the next line.", fontsize=8)
    second = document.new_page(width=400, height=400)
    second.insert_text((20, 35), "Details", fontsize=20, fontname="hebo")
    second.insert_text((20, 85), "Destination body.", fontsize=10)
    document[0].insert_link(
        {
            "kind": pymupdf.LINK_GOTO,
            "from": pymupdf.Rect(20, 73, 90, 89),
            "page": 1,
            "to": pymupdf.Point(20, 35),
        }
    )


def assets(document) -> None:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 12, 12), False)
    pixmap.clear_with(0x336699)
    image = ROOT / "source.png"
    pixmap.save(image)
    page = document.new_page(width=400, height=500)
    page.insert_text((20, 35), "Asset placement", fontsize=20, fontname="hebo")
    page.insert_text((20, 80), "Before the first placement.", fontsize=10)
    page.insert_image(pymupdf.Rect(20, 110, 120, 190), filename=image)
    page.insert_text((20, 205), "Figure 1: First placement", fontsize=9, fontname="heit")
    page.insert_text((20, 245), "Between placements.", fontsize=10)
    page.insert_image(pymupdf.Rect(220, 280, 320, 360), filename=image)
    page.insert_text((220, 375), "Figure 2: Reused image", fontsize=9, fontname="heit")
    page.insert_text((20, 420), "After both placements.", fontsize=10)
    image.unlink()


def rotated_code_table(document) -> None:
    page = document.new_page(width=500, height=600)
    page.insert_text((20, 35), "Mixed structures", fontsize=20, fontname="hebo")
    page.insert_text((460, 220), "Rotated margin label", fontsize=9, rotate=90)
    page.insert_text((20, 90), "def greet(name):", fontsize=9, fontname="cour")
    page.insert_text((20, 103), "return f'Hello {name}'", fontsize=9, fontname="cour")
    for y, values, xs in (
        (170, ("Region", "Revenue"), (20, 330)),
        (190, ("North", "1,240"), (20, 345)),
        (210, ("South", "980"), (20, 355)),
    ):
        for x, value in zip(xs, values, strict=True):
            page.insert_text((x, y), value, fontsize=10)
    page.insert_text((20, 228), "Table 1: Revenue", fontsize=9, fontname="heit")


for name, drawing in (
    ("columns", columns),
    ("furniture", furniture),
    ("three-columns", three_columns),
    ("links-footnotes", links_footnotes),
    ("assets", assets),
    ("rotated-code-table", rotated_code_table),
):
    save(name, drawing)
