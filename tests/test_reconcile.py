from pdf_to_carve.reconcile import reconcile_hybrid


def text(value: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": value}]


def test_hybrid_rejects_wording_changes_and_accepts_code_whitespace_repairs() -> None:
    baseline = {
        "version": 1,
        "blocks": [
            {"type": "paragraph", "content": text("Exact source wording.")},
            {"type": "code_block", "text": "if (true) {\nreturn 1;\n}", "language": "php"},
        ],
    }
    visual = {
        "version": 1,
        "blocks": [
            {"type": "paragraph", "content": text("Changed source wording.")},
            {"type": "code_block", "text": "if (true) {\n    return 1;\n}", "language": "js"},
        ],
    }
    result = reconcile_hybrid(baseline, visual)
    assert result["blocks"][0] == baseline["blocks"][0]
    assert result["blocks"][1]["text"] == "if (true) {\n    return 1;\n}"
    assert result["blocks"][1]["language"] == "php"


def test_hybrid_accepts_exact_structural_upgrade_and_keeps_table_alignment() -> None:
    baseline = {
        "version": 1,
        "blocks": [
            {
                "type": "table",
                "headers": [text("Name"), text("Value")],
                "alignments": ["left", "right"],
                "rows": [[text("A"), text("1")]],
            }
        ],
    }
    visual = {
        "version": 1,
        "blocks": [
            {
                "type": "table",
                "headers": [text("Name"), text("Value")],
                "rows": [[text("A"), text("1")]],
            }
        ],
    }
    result = reconcile_hybrid(baseline, visual)
    assert result["blocks"][0]["alignments"] == ["left", "right"]


def test_hybrid_requires_confident_geometry_for_semantic_diagram_upgrade() -> None:
    baseline = {"version": 1, "blocks": [{"type": "paragraph", "content": text("Plan Build Ship")}]}
    diagram = {"type": "code_block", "language": "mermaid", "text": "Plan --> Build --> Ship"}
    without_evidence = {"version": 1, "blocks": [diagram]}
    assert reconcile_hybrid(baseline, without_evidence)["blocks"] == baseline["blocks"]

    with_evidence = {
        "version": 1,
        "blocks": [diagram],
        "provenance": [{"block": 0, "page": 1, "bbox": [0, 0, 100, 40], "confidence": 0.9}],
    }
    assert reconcile_hybrid(baseline, with_evidence)["blocks"][0]["language"] == "mermaid"


def test_hybrid_remaps_and_combines_provenance_after_structural_repair() -> None:
    baseline = {
        "version": 1,
        "blocks": [
            {"type": "paragraph", "content": text("One")},
            {"type": "paragraph", "content": text("Two")},
            {"type": "paragraph", "content": text("After")},
        ],
        "provenance": [
            {"block": 0, "page": 1, "warnings": ["first evidence"]},
            {"block": 1, "page": 1},
            {"block": 2, "page": 2, "warnings": ["after evidence"]},
        ],
    }
    visual = {
        "version": 1,
        "blocks": [
            {
                "type": "list",
                "items": [{"content": text("One")}, {"content": text("Two")}],
            }
        ],
        "provenance": [{"block": 0, "page": 1, "bbox": [0, 0, 100, 40], "confidence": 0.95}],
    }
    result = reconcile_hybrid(baseline, visual)
    assert [block["type"] for block in result["blocks"]] == ["list", "paragraph"]
    assert [entry["block"] for entry in result["provenance"]] == [0, 1]
    assert result["provenance"][1]["page"] == 2
    assert "first evidence" in result["provenance"][0]["warnings"]
