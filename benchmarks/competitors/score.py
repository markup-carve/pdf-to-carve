#!/usr/bin/env python3
"""Recompute the committed competitor benchmark from raw normalized outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
GENERIC_KINDS = {"document", "frontmatter", "paragraph", "text"}


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def ratio(expected: str, actual: str, *, words: bool = False) -> float:
    left: Any = normalize(expected)
    right: Any = normalize(actual)
    if words:
        left, right = left.split(), right.split()
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def ast_kinds(path: Path) -> set[str]:
    result: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("type"), str):
                result.add(value["type"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(json.loads(path.read_text()))
    return result - GENERIC_KINDS


def calculate() -> dict[str, Any]:
    runs = json.loads((ROOT / "runs.json").read_text())
    fixtures = [item["id"] for item in json.loads((ROOT / "fixtures.json").read_text())["fixtures"]]
    tools = []
    for tool in runs["tools"]:
        samples = []
        for fixture in fixtures:
            record = tool["documents"].get(fixture, {"status": "not_attempted"})
            sample: dict[str, Any] = {"fixture": fixture, "status": record["status"]}
            output = ROOT / "raw" / tool["id"] / f"{fixture}.plain.txt"
            truth = ROOT / "raw" / "truth" / f"{fixture}.plain.txt"
            if record["status"] == "complete" and output.is_file() and output.stat().st_size:
                expected, actual = truth.read_text(), output.read_text()
                sample["character"] = round(ratio(expected, actual), 6)
                sample["word"] = round(ratio(expected, actual, words=True), 6)
                candidate_ast = ROOT / "raw" / tool["id"] / f"{fixture}.ast.json"
                truth_ast = ROOT / "raw" / "truth" / f"{fixture}.ast.json"
                if candidate_ast.is_file():
                    expected_kinds, actual_kinds = ast_kinds(truth_ast), ast_kinds(candidate_ast)
                    recovered = expected_kinds & actual_kinds
                    sample["structure"] = {
                        "recovered": len(recovered),
                        "expected": len(expected_kinds),
                        "recall": round(len(recovered) / len(expected_kinds), 6),
                    }
            samples.append(sample)
        scored = [sample for sample in samples if "character" in sample]
        result = {
            "id": tool["id"],
            "name": tool["name"],
            "version": tool["version"],
            "completed": len(scored),
            "corpus_size": len(fixtures),
            "samples": samples,
        }
        seconds = [
            record["seconds"] for record in tool["documents"].values() if "seconds" in record
        ]
        rss = [record["rss_kb"] for record in tool["documents"].values() if "rss_kb" in record]
        result["observed_seconds"] = seconds
        result["observed_rss_kb"] = rss
        if scored:
            result["mean_character"] = round(statistics.mean(x["character"] for x in scored), 6)
            result["mean_word"] = round(statistics.mean(x["word"] for x in scored), 6)
            structured = [x["structure"]["recall"] for x in scored if "structure" in x]
            result["mean_structure"] = round(statistics.mean(structured), 6) if structured else None
        tools.append(result)
    artifacts = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "raw").rglob("*"))
        if path.is_file()
    }
    return {
        "schema": 1,
        "metric": "SequenceMatcher, NFC + collapsed whitespace",
        "raw_artifacts": artifacts,
        "tools": tools,
    }


def report(results: dict[str, Any]) -> str:
    lines = [
        "# Competitor benchmark — August 2026",
        "",
        "This report is generated from the committed raw observations by `score.py`.",
        "Higher fidelity and structural-recall scores are better. Completion is never folded",
        "into a quality average. See [README.md](README.md) for method and limitations.",
        "",
        "| Extractor | Version | Completed | Character | Word | Structure |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    ranked = sorted(results["tools"], key=lambda item: item.get("mean_character", -1), reverse=True)
    for tool in ranked:
        character = f"{tool['mean_character']:.3f}" if "mean_character" in tool else "n/a"
        word = f"{tool['mean_word']:.3f}" if "mean_word" in tool else "n/a"
        structure = tool.get("mean_structure")
        structure_text = f"{structure:.3f}" if structure is not None else "n/a"
        lines.append(
            f"| {tool['name']} | {tool['version']} | {tool['completed']}/{tool['corpus_size']} "
            f"| {character} | {word} | {structure_text} |"
        )
    lines.extend(
        [
            "",
            "## Per-document evidence",
            "",
            "| Extractor | Fixture | Status | Character | Word | Structural kinds |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for tool in results["tools"]:
        for sample in tool["samples"]:
            structure = sample.get("structure")
            kinds = f"{structure['recovered']}/{structure['expected']}" if structure else "n/a"
            lines.append(
                f"| {tool['name']} | {sample['fixture']} | {sample['status']} | "
                f"{sample.get('character', 'n/a')} | {sample.get('word', 'n/a')} | {kinds} |"
            )
    lines.extend(
        [
            "",
            "## Operational observations",
            "",
            "Times and peak RSS are sequential local samples, not normalized throughput.",
            "Batch-only measurements and timeout details remain in `runs.json`.",
            "",
            "| Extractor | Per-document seconds | Peak RSS MiB |",
            "| --- | ---: | ---: |",
        ]
    )
    for tool in results["tools"]:
        seconds = ", ".join(f"{value:.2f}" for value in tool["observed_seconds"]) or "n/a"
        rss = ", ".join(f"{value / 1024:.1f}" for value in tool["observed_rss_kb"]) or "n/a"
        lines.append(f"| {tool['name']} | {seconds} | {rss} |")
    lines.extend(
        [
            "",
            "## Reading the result",
            "",
            "The three Carve hybrid variants occupy the leading positions on this corpus:",
            "Claude Opus has the highest character mean, Claude Sonnet the highest word and",
            "structural-kind means, and Codex sits between them. Marker has the strongest",
            "structural-kind recall among third-party destination pipelines. Docling has a",
            "strong single-document text score but timed out before completing the corpus.",
            "Plain-text-only output has no structural score.",
            "",
            "One vision competitor is listed but unscored: the available provider account was",
            "credit-exhausted. The tool logged the page failure, returned exit status zero, and",
            "created an empty output. The sanitized observation is committed under `raw/`.",
            "That is an operational finding, not a fidelity comparison.",
            "",
            "These independently recomputed scores intentionally supersede the earlier PR-summary",
            "table, whose exact scoring script and intermediate normalization were not retained.",
            "No claim should rely on that older table when this auditable report is available.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    results = calculate()
    results_text = json.dumps(results, indent=2, sort_keys=True) + "\n"
    report_text = report(results)
    if args.write:
        (ROOT / "results.json").write_text(results_text)
        (ROOT / "REPORT.md").write_text(report_text)
        return 0
    expected_results = (ROOT / "results.json").read_text()
    expected_report = (ROOT / "REPORT.md").read_text()
    if results_text != expected_results or report_text != expected_report:
        raise SystemExit("benchmark artifacts are stale; run score.py --write")
    print("benchmark artifacts are reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
