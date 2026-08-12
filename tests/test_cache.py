import json
from pathlib import Path

from pdf_to_carve.cache import JsonCache, cache_key


def test_cache_key_tracks_content_model_and_prompt(tmp_path: Path) -> None:
    page = tmp_path / "page.png"
    page.write_bytes(b"one")
    first = cache_key(files=[page], model="m", prompt="p")
    assert first == cache_key(files=[page], model="m", prompt="p")
    page.write_bytes(b"two")
    assert first != cache_key(files=[page], model="m", prompt="p")
    assert first != cache_key(files=[page], model="other", prompt="p")


def test_cache_round_trip_and_corrupt_entry_is_a_miss(tmp_path: Path) -> None:
    cache = JsonCache(tmp_path)
    cache.put("key", {"version": 1, "blocks": []})
    assert cache.get("key") == {"version": 1, "blocks": []}
    (tmp_path / "key.json").write_text("not json")
    assert cache.get("key") is None
    (tmp_path / "key.json").write_text(json.dumps([]))
    assert cache.get("key") is None
    assert cache.get("missing") is None
