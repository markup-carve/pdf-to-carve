"""Content-addressed cache for expensive extraction responses."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def cache_key(*, files: list[Path], model: str, prompt: str, schema_version: int = 1) -> str:
    digest = hashlib.sha256()
    digest.update(f"schema={schema_version}\0model={model}\0prompt={prompt}\0".encode())
    for path in files:
        digest.update(path.read_bytes())
    return digest.hexdigest()


class JsonCache:
    def __init__(self, directory: Path):
        self.directory = directory.expanduser().resolve()

    def get(self, key: str) -> dict[str, Any] | None:
        target = self.directory / f"{key}.json"
        if not target.is_file():
            return None
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / f"{key}.json"
        temporary = self.directory / f".{key}.{os.getpid()}.tmp"
        temporary.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(target)
