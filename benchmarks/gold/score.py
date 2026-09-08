"""Reproduce the deterministic gold-set accuracy report."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pdf_to_carve.pipeline import ConversionOptions, convert

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "pdf_corpus"
MANIFEST = Path(__file__).with_name("manifest.json")


def edit_counts(reference: Sequence[Any], candidate: Sequence[Any]) -> dict[str, int]:
    """Return minimum Levenshtein insertions, deletions, and substitutions."""
    rows = [[(0, 0, 0, 0) for _ in range(len(candidate) + 1)] for _ in range(len(reference) + 1)]
    for index in range(1, len(reference) + 1):
        rows[index][0] = (index, 0, index, 0)
    for index in range(1, len(candidate) + 1):
        rows[0][index] = (index, index, 0, 0)
    for left in range(1, len(reference) + 1):
        for right in range(1, len(candidate) + 1):
            if reference[left - 1] == candidate[right - 1]:
                rows[left][right] = rows[left - 1][right - 1]
                continue
            deletion = rows[left - 1][right]
            insertion = rows[left][right - 1]
            substitution = rows[left - 1][right - 1]
            choices = [
                (deletion[0] + 1, deletion[1], deletion[2] + 1, deletion[3]),
                (insertion[0] + 1, insertion[1] + 1, insertion[2], insertion[3]),
                (substitution[0] + 1, substitution[1], substitution[2], substitution[3] + 1),
            ]
            rows[left][right] = min(choices)
    distance, insertions, deletions, substitutions = rows[-1][-1]
    return {
        "distance": distance,
        "insertions": insertions,
        "deletions": deletions,
        "substitutions": substitutions,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    chars = sum(case["characters"] for case in cases)
    words = sum(case["words"] for case in cases)
    char_errors = sum(case["character_errors"]["distance"] for case in cases)
    word_errors = sum(case["word_errors"]["distance"] for case in cases)
    return {
        "documents": len(cases),
        "exact_documents": sum(case["exact"] for case in cases),
        "document_accuracy": sum(case["exact"] for case in cases) / len(cases),
        "character_error_rate": char_errors / chars if chars else 0.0,
        "word_error_rate": word_errors / words if words else 0.0,
        "character_errors": {
            key: sum(case["character_errors"][key] for case in cases)
            for key in ("insertions", "deletions", "substitutions")
        },
        "word_errors": {
            key: sum(case["word_errors"][key] for case in cases)
            for key in ("insertions", "deletions", "substitutions")
        },
    }


def build_report() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = []
    for item in manifest["cases"]:
        pdf = CORPUS / f"{item['name']}.pdf"
        gold = CORPUS / "expected" / f"{item['name']}.crv"
        if sha256(pdf) != item["pdf_sha256"] or sha256(gold) != item["gold_sha256"]:
            raise RuntimeError(f"gold inputs changed without manifest review: {item['name']}")
        with tempfile.TemporaryDirectory(prefix="pdf-to-carve-gold-") as directory:
            assets = Path(directory) / "assets" if item["name"] == "assets" else None
            actual = convert(pdf, ConversionOptions(mode="text", assets_dir=assets)).source
        expected = gold.read_text(encoding="utf-8")
        char_errors = edit_counts(expected, actual)
        expected_words = expected.split()
        word_errors = edit_counts(expected_words, actual.split())
        cases.append(
            {
                "name": item["name"],
                "class": item["class"],
                "features": item["features"],
                "exact": actual == expected,
                "characters": len(expected),
                "words": len(expected_words),
                "character_errors": char_errors,
                "word_errors": word_errors,
            }
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["class"]].append(case)
    return {
        "schema": 1,
        "mode": manifest["mode"],
        "metrics": {
            "document_accuracy": "exact generated Carve / documents",
            "character_error_rate": "Levenshtein character edits / gold characters",
            "word_error_rate": "Levenshtein token edits / gold whitespace tokens",
        },
        "overall": _aggregate(cases),
        "by_class": {name: _aggregate(values) for name, values in sorted(grouped.items())},
        "cases": cases,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the checked-in human summary from the machine-readable result."""
    labels = {
        "complex-tables": "Complex tables",
        "mixed-layout": "Mixed layout",
        "multi-column": "Multi-column",
        "references": "References",
        "repeated-furniture": "Repeated furniture",
        "visual-assets": "Visual assets",
    }
    overall = report["overall"]
    documents = overall["documents"]
    character_errors = overall["character_errors"]
    word_errors = overall["word_errors"]
    lines = [
        "# Born-digital extraction accuracy",
        "",
        "- Mode: deterministic PDFium text extraction",
        f"- Gold set: {documents} generated, hand-checked documents",
        "",
        "## Results",
        "",
        "| Document class | Documents | Exact | Character error rate | Word error rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, result in report["by_class"].items():
        lines.append(
            f"| {labels.get(name, name)} | {result['documents']} | "
            f"{result['exact_documents']}/{result['documents']} | "
            f"{result['character_error_rate']:.2%} | {result['word_error_rate']:.2%} |"
        )
    lines.extend(
        [
            f"| **Overall** | **{overall['documents']}** | "
            f"**{overall['exact_documents']}/{overall['documents']}** | "
            f"**{overall['character_error_rate']:.2%}** | **{overall['word_error_rate']:.2%}** |",
            "",
            "Character edits: "
            f"{character_errors['insertions']} insertions, "
            f"{character_errors['deletions']} deletions, and "
            f"{character_errors['substitutions']} substitutions. Word edits:",
            f"{word_errors['insertions']} insertions, {word_errors['deletions']} deletions, and "
            f"{word_errors['substitutions']} substitutions.",
            "Document accuracy requires byte-for-byte equality with the complete Carve",
            "answer key; it is not a text-only comparison.",
            "",
            "Character error rate is minimum Levenshtein character edits divided by gold",
            "characters. Word error rate uses whitespace-delimited tokens. The published",
            "machine-readable counts, including every case and error type, are in",
            "`results.json`.",
            "",
            "## Interpretation",
            "",
            "The result establishes deterministic regression accuracy for these fixtures.",
            "The answer keys are the same pinned, hand-checked snapshots used by the release",
            "tests, so a green release gate necessarily reports zero error here. The measures",
            "are a determinism check, not an independent accuracy estimate.",
            "It does not estimate performance on natural document populations, scans, or",
            f"cloud-vision providers. The set contains only {documents} small generated documents;",
            "most strata have one member. Its purpose is to make known layout behavior",
            "reproducible and failures measurable while a larger, independently sourced set",
            "is assembled.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = build_report()
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    if args.report:
        args.report.write_text(render_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
