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


def test_pdfium_places_raster_figure_and_attaches_explicit_caption(tmp_path: Path) -> None:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), False)
    pixmap.clear_with(0x336699)
    image = tmp_path / "source.png"
    pixmap.save(image)
    pdf = tmp_path / "placed.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=240)
    page.insert_text((20, 30), "Before image", fontsize=10)
    page.insert_image(pymupdf.Rect(20, 60, 120, 140), filename=image)
    page.insert_text((20, 155), "Figure 1: Blue sample", fontsize=9, fontname="heit")
    page.insert_text((20, 190), "After image", fontsize=10)
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf, assets_dir=tmp_path / "assets")["blocks"]
    assert [block["type"] for block in blocks] == ["paragraph", "figure", "paragraph"]
    assert blocks[1]["src"] == "assets/page-1-raster-1.png"
    assert blocks[1]["caption"][0]["text"] == "Figure 1: Blue sample"


def test_pdfium_page_limits_fail_closed(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _pdf(pdf)
    try:
        render_pages(pdf, tmp_path, 1, None, dpi=100, max_pages=0)
    except ValueError as exc:
        assert "maximum is 0" in str(exc)
    else:
        raise AssertionError("page limit was not enforced")


def test_pdfium_suppresses_repeated_headers_footers_and_page_numbers(tmp_path: Path) -> None:
    pdf = tmp_path / "furniture.pdf"
    document = pymupdf.open()
    for number in (1, 2):
        page = document.new_page(width=400, height=500)
        page.insert_text((20, 25), "Quarterly report", fontsize=9)
        page.insert_text((20, 100), f"Unique body {number}", fontsize=11)
        page.insert_text((180, 485), f"Page {number}", fontsize=9)
    document.save(pdf)
    document.close()

    source = extract_text_pdf(pdf)
    text = str(source)
    assert "Quarterly report" not in text
    assert "Page 1" not in text and "Page 2" not in text
    assert "Unique body 1" in text and "Unique body 2" in text


def test_pdfium_uses_column_major_reading_order_for_substantial_columns(tmp_path: Path) -> None:
    pdf = tmp_path / "columns.pdf"
    document = pymupdf.open()
    page = document.new_page(width=500, height=400)
    page.insert_text((20, 30), "Two column article", fontsize=20, fontname="hebo")
    for y, left, right in (
        (80, "Left column first line has enough width.", "Right column first line has width."),
        (94, "Left column second line continues here.", "Right column second line continues."),
    ):
        page.insert_text((20, y), left, fontsize=10)
        page.insert_text((270, y), right, fontsize=10)
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf)["blocks"]
    values = [block.get("content", [{}])[0].get("text", "") for block in blocks]
    assert values == [
        "Two column article",
        "Left column first line has enough width. Left column second line continues here.",
        "Right column first line has width. Right column second line continues.",
    ]


def test_pdfium_preserves_rotated_text_as_content(tmp_path: Path) -> None:
    pdf = tmp_path / "rotated.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((30, 100), "Normal body text", fontsize=10)
    page.insert_text((250, 250), "Rotated label", fontsize=10, rotate=90)
    document.save(pdf)
    document.close()

    assert "Rotated label" in str(extract_text_pdf(pdf))


def test_pdfium_pairs_superscript_reference_with_bottom_footnote(tmp_path: Path) -> None:
    pdf = tmp_path / "footnote.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((20, 80), "Claim", fontsize=10)
    page.insert_text((47, 76), "1", fontsize=7)
    page.insert_text((20, 270), "1 Footnote detail", fontsize=8)
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf)["blocks"]
    assert blocks == [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Claim "},
                {
                    "type": "footnote",
                    "children": [{"type": "text", "text": "Footnote detail"}],
                },
            ],
        }
    ]


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
    page.insert_text((20, 398), "Table 1: Values", fontsize=9, fontname="heit")
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
    assert blocks[8]["alignments"] == ["left", "left"]
    assert blocks[8]["caption"][0]["text"] == "Table 1: Values"


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


def test_pdfium_resolves_internal_goto_links_to_target_heading(tmp_path: Path) -> None:
    pdf = tmp_path / "internal-link.pdf"
    document = pymupdf.open()
    first = document.new_page(width=400, height=300)
    first.insert_text((20, 30), "Contents", fontsize=20, fontname="hebo")
    first.insert_text((20, 70), "Read details", fontsize=10)
    first.insert_text((20, 100), "Introduction body text", fontsize=10)
    second = document.new_page(width=400, height=300)
    second.insert_text((20, 30), "Details", fontsize=20, fontname="hebo")
    second.insert_text((20, 70), "Detailed body text", fontsize=10)
    first = document[0]
    first.insert_link(
        {
            "kind": pymupdf.LINK_GOTO,
            "from": pymupdf.Rect(20, 58, 90, 74),
            "page": 1,
            "to": pymupdf.Point(20, 30),
        }
    )
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf)["blocks"]
    link = blocks[1]["content"][0]
    assert link["type"] == "link" and link["url"] == "#page-2"
    details = next(block for block in blocks if block.get("id") == "page-2")
    assert details["content"][0]["text"] == "Details"


def test_pdfium_anchors_internal_destination_without_a_heading(tmp_path: Path) -> None:
    pdf = tmp_path / "internal-paragraph.pdf"
    document = pymupdf.open()
    first = document.new_page(width=400, height=300)
    first.insert_text((20, 70), "Read destination", fontsize=10)
    second = document.new_page(width=400, height=300)
    second.insert_text((20, 70), "Paragraph destination", fontsize=10)
    document[0].insert_link(
        {
            "kind": pymupdf.LINK_GOTO,
            "from": pymupdf.Rect(20, 58, 110, 74),
            "page": 1,
            "to": pymupdf.Point(20, 70),
        }
    )
    document.save(pdf)
    document.close()

    blocks = extract_text_pdf(pdf)["blocks"]
    assert blocks[0]["content"][0]["url"] == "#page-2"
    assert blocks[2]["id"] == "page-2"


def test_pdfium_merges_repeated_table_header_across_page_break(tmp_path: Path) -> None:
    pdf = tmp_path / "continued-table.pdf"
    document = pymupdf.open()
    for values in (("A", "1", "B", "2"), ("C", "3", "D", "4")):
        page = document.new_page(width=400, height=300)
        for y, row in ((70, ("Name", "Value")), (90, values[:2]), (110, values[2:])):
            page.insert_text((20, y), row[0], fontsize=10)
            page.insert_text((220, y), row[1], fontsize=10)
    document.save(pdf)
    document.close()

    raw = extract_text_pdf(pdf)
    tables = [block for block in raw["blocks"] if block["type"] == "table"]
    assert len(tables) == 1 and len(tables[0]["rows"]) == 4
    assert "merged 1 table continuation" in " ".join(raw["diagnostics"])


def test_pdfium_infers_code_language_only_from_strong_syntax(tmp_path: Path) -> None:
    pdf = tmp_path / "code.pdf"
    document = pymupdf.open()
    page = document.new_page(width=500, height=300)
    page.insert_text((20, 30), "Code samples", fontsize=20, fontname="hebo")
    page.insert_text(
        (20, 60), "function greet(string $name): string {", fontsize=10, fontname="cour"
    )
    page.insert_text((20, 72), 'return "Hello, {$name}!";', fontsize=10, fontname="cour")
    page.insert_text((20, 84), "}", fontsize=10, fontname="cour")
    page.insert_text((20, 102), "Between samples.", fontsize=10)
    page.insert_text((20, 120), "plain monospace prose", fontsize=10, fontname="cour")
    document.save(pdf)
    document.close()

    code = [block for block in extract_text_pdf(pdf)["blocks"] if block["type"] == "code_block"]
    assert code[0]["language"] == "php"
    assert "language" not in code[1]


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
    table = next(block for block in blocks if block["type"] == "table")
    assert table["alignments"] == ["left", "right", "right"]
    code = next(block for block in blocks if block["type"] == "code_block")
    assert code["language"] == "php"


def test_published_vector_figure_is_preserved_with_visible_labels(tmp_path: Path) -> None:
    pdf = Path(__file__).parents[1] / "docs/comparisons/php-pdfparser-v3.3.0/input.pdf"
    assets = tmp_path / "assets"
    blocks = extract_text_pdf(pdf, assets_dir=assets)["blocks"]
    figure = next(block for block in blocks if block["type"] == "figure")
    assert figure == {
        "type": "figure",
        "src": "assets/page-2-vector-1.png",
        "alt": "Plan, Build, Ship",
    }
    assert (assets / "page-2-vector-1.png").is_file()
