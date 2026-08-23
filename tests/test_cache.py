import json
from concurrent.futures import ThreadPoolExecutor
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


def test_cache_key_delimits_page_contents(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"ab")
    second.write_bytes(b"c")
    combined = cache_key(files=[first, second], model="m", prompt="p")
    first.write_bytes(b"a")
    second.write_bytes(b"bc")
    assert combined != cache_key(files=[first, second], model="m", prompt="p")


def test_cache_round_trip_and_corrupt_entry_is_a_miss(tmp_path: Path) -> None:
    cache = JsonCache(tmp_path)
    cache.put("key", {"version": 1, "blocks": []})
    assert cache.get("key") == {"version": 1, "blocks": []}
    (tmp_path / "key.json").write_text("not json")
    assert cache.get("key") is None
    (tmp_path / "key.json").write_text(json.dumps([]))
    assert cache.get("key") is None
    assert cache.get("missing") is None


def test_concurrent_cache_writes_do_not_share_a_temporary_file(tmp_path: Path) -> None:
    cache = JsonCache(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda value: cache.put("key", {"value": value}), range(40)))
    assert cache.get("key") in ({"value": value} for value in range(40))
    assert not list(tmp_path.glob("*.tmp"))
