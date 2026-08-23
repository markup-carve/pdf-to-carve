from pathlib import Path

import pymupdf

from pdf_to_carve.pdfium_backend import (
    extract_embedded_images,
    extract_text_pdf,
    positioned_text,
    render_pages,
    text_coverage,
)


def _pdf(path: Path, image: Path | None = None) -> None:
    document = pymupdf.open()
    document.set_metadata({"title": "PDFium fixture", "author": "Tests"})
    page = document.new_page(width=300, height=200)
    page.insert_text((20, 30), "Large heading", fontsize=20)
    page.insert_text((20, 60), "Body text", fontsize=10)
    if image:
        page.insert_image(pymupdf.Rect(20, 80, 50, 110), filename=image)
        page.insert_image(pymupdf.Rect(60, 80, 90, 110), filename=image)
    document.save(path)
    document.close()


def test_pdfium_extracts_metadata_text_positions_and_render(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _pdf(pdf)
    extracted = extract_text_pdf(pdf)
    assert extracted["title"] == "PDFium fixture"
    assert extracted["author"] == "Tests"
    assert extracted["blocks"][0]["type"] == "heading"
    assert extracted["blocks"][1]["content"][0]["text"] == "Body text"
    assert text_coverage(pdf) == len("LargeheadingBodytext")
    evidence = positioned_text(pdf)
    assert evidence[0]["page"] == 1
    assert len(evidence[0]["bbox"]) == 4
    pages = render_pages(pdf, tmp_path, 1, None, dpi=100, max_pages=1)
    assert pages[0].is_file()


def test_pdfium_extracts_and_deduplicates_images(tmp_path: Path) -> None:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), False)
    pixmap.clear_with(0x336699)
    image = tmp_path / "source.png"
    pixmap.save(image)
    pdf = tmp_path / "input.pdf"
    _pdf(pdf, image)
    assets = extract_embedded_images(pdf, tmp_path / "assets")
    assert len(assets) == 1
    assert assets[0].suffix == ".png"


def test_pdfium_page_limits_fail_closed(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _pdf(pdf)
    try:
        render_pages(pdf, tmp_path, 1, None, dpi=100, max_pages=0)
    except ValueError as exc:
        assert "maximum is 0" in str(exc)
    else:
        raise AssertionError("page limit was not enforced")


def test_pdfium_text_mode_recovers_conservative_document_structure(tmp_path: Path) -> None:
    pdf = tmp_path / "structured.pdf"
    document = pymupdf.open()
    page = document.new_page(width=500, height=700)
    page.insert_text((20, 30), "Document title", fontsize=24, fontname="hebo")
    page.insert_text((20, 65), "Introduction", fontsize=18, fontname="hebo")
    page.insert_text((20, 90), "A wrapped paragraph that", fontsize=10)
    page.insert_text((20, 101), "continues on this line.", fontsize=10)
    page.insert_text((20, 125), "A separate paragraph.", fontsize=10)
    page.insert_text((20, 150), "Normal ", fontsize=10)
    page.insert_text((54, 150), "bold", fontsize=10, fontname="hebo")
    page.insert_text((76, 150), " and ", fontsize=10)
    page.insert_text((101, 150), "italic", fontsize=10, fontname="heit")
    for y, value in ((180, "First"), (194, "Second"), (208, "Third")):
        page.insert_text((40, y), value, fontsize=10)
    for y, value in ((235, "1. One"), (249, "2. Two"), (263, "3. Three")):
        page.insert_text((30, y), value, fontsize=10)
    page.insert_text((30, 295), "print('one')", fontsize=10, fontname="cour")
    page.insert_text((30, 307), "print('two')", fontsize=10, fontname="cour")
    for y, values in (
        (340, ("Name", "Value")),
        (360, ("A", "1")),
        (380, ("B", "2")),
    ):
        page.insert_text((20, y), values[0], fontsize=10)
        page.insert_text((180, y), values[1], fontsize=10)
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf)["blocks"]
    assert [(block["type"], block.get("level")) for block in blocks[:2]] == [
        ("heading", 1),
        ("heading", 2),
    ]
    assert blocks[2]["content"][0]["text"] == ("A wrapped paragraph that continues on this line.")
    assert blocks[3]["content"][0]["text"] == "A separate paragraph."
    assert [node["type"] for node in blocks[4]["content"]] == [
        "text",
        "strong",
        "text",
        "emphasis",
    ]
    assert blocks[5]["type"] == "list" and blocks[5]["ordered"] is False
    assert blocks[6]["type"] == "list" and blocks[6]["ordered"] is True
    assert blocks[7]["type"] == "code_block"
    assert blocks[8]["type"] == "table"


def test_pdfium_recovers_links_decorations_and_conservative_quotes(tmp_path: Path) -> None:
    pdf = tmp_path / "decorated.pdf"
    document = pymupdf.open()
    page = document.new_page(width=500, height=300)
    page.insert_text((20, 30), "Document title", fontsize=20, fontname="hebo")
    page.insert_text((20, 60), "Ordinary body text establishes the margin.", fontsize=10)

    link_text = "linked text"
    link_width = pymupdf.get_text_length(link_text, fontsize=10)
    page.insert_text((20, 90), link_text, fontsize=10)
    page.insert_link(
        {
            "kind": pymupdf.LINK_URI,
            "from": pymupdf.Rect(20, 79, 20 + link_width, 92),
            "uri": "https://example.com/docs",
        }
    )

    underline_text = "underlined text"
    underline_width = pymupdf.get_text_length(underline_text, fontsize=10)
    page.insert_text((20, 120), underline_text, fontsize=10)
    page.draw_line((20, 121), (20 + underline_width, 121), color=(0, 0, 0), width=0.75)

    highlight_text = "highlighted text"
    highlight_width = pymupdf.get_text_length(highlight_text, fontsize=10)
    page.draw_rect(
        pymupdf.Rect(20, 132, 20 + highlight_width, 144),
        color=None,
        fill=(1, 0.95, 0.65),
    )
    page.insert_text((20, 143), highlight_text, fontsize=10)

    quote = "A sufficiently long italic quotation is visibly indented from the body margin."
    page.insert_text((35, 175), quote, fontsize=10, fontname="heit")
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf)["blocks"]
    assert blocks[2]["content"] == [
        {
            "type": "link",
            "url": "https://example.com/docs",
            "children": [{"type": "text", "text": link_text}],
        }
    ]
    assert blocks[3]["content"][0]["type"] == "underline"
    assert blocks[4]["content"][0]["type"] == "highlight"
    assert blocks[5] == {
        "type": "quote",
        "content": [{"type": "text", "text": quote}],
    }

    evidence = positioned_text(pdf)
    linked = next(item for item in evidence if item["text"] == link_text)
    assert linked["urls"] == ["https://example.com/docs"]


def test_published_markdown_fixture_keeps_supported_pdf_semantics() -> None:
    pdf = Path(__file__).parents[1] / "docs/comparisons/php-pdfparser-v3.3.0/input.pdf"
    blocks = extract_text_pdf(pdf)["blocks"]
    assert [block["type"] for block in blocks].count("table") == 1
    assert [block["type"] for block in blocks].count("quote") == 1

    inline_types = {node["type"] for block in blocks for node in block.get("content", [])}
    assert {"link", "underline", "highlight", "superscript", "subscript"} <= inline_types
    link = next(
        node for block in blocks for node in block.get("content", []) if node["type"] == "link"
    )
    assert link["url"] == "https://example.com/docs"
