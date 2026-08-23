"""Content-addressed cache for expensive extraction responses."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def cache_key(*, files: list[Path], model: str, prompt: str, schema_version: int = 1) -> str:
    digest = hashlib.sha256()
    digest.update(f"schema={schema_version}\0model={model}\0prompt={prompt}\0".encode())
    digest.update(len(files).to_bytes(8, "big"))
    for path in files:
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
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
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.directory, prefix=f".{key}.{os.getpid()}.", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, allow_nan=False)
                handle.write("\n")
            for attempt in range(10):
                try:
                    temporary.replace(target)
                    break
                except PermissionError:
                    if attempt == 9:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)
