#!/usr/bin/env python3
"""Fetch and verify the immutable public benchmark PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    manifest = json.loads((Path(__file__).parent / "fixtures.json").read_text())
    args.directory.mkdir(parents=True, exist_ok=True)
    for fixture in manifest["fixtures"]:
        for kind, suffix in (("pdf", ".pdf"), ("source", ".crv")):
            target = args.directory / f"{fixture['id']}{suffix}"
            with urllib.request.urlopen(fixture[f"{kind}_url"], timeout=60) as response:
                content = response.read()
            digest = hashlib.sha256(content).hexdigest()
            if digest != fixture[f"{kind}_sha256"]:
                raise ValueError(f"hash mismatch for {fixture['id']} {kind}: {digest}")
            target.write_bytes(content)
            print(f"{fixture['id']}{suffix}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
