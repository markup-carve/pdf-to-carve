import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from pdf_to_carve.vision import VisionError, transcribe_images


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": '{"version":1,"blocks":[]}'}}]}
        ).encode()


def test_provider_builds_openai_compatible_json_request(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    with patch("urllib.request.urlopen", return_value=Response()) as opened:
        assert transcribe_images([image], model="vision-test", api_key="secret") == {
            "version": 1,
            "blocks": [],
        }
    request = opened.call_args.args[0]
    body = json.loads(request.data)
    assert request.headers["Authorization"] == "Bearer secret"
    assert body["model"] == "vision-test"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][1]["content"][1]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )


def test_provider_requires_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(VisionError, match="OPENAI_API_KEY"):
        transcribe_images([tmp_path / "missing.png"], model="test")


def test_provider_retries_transient_failure(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    transient = urllib.error.URLError("temporary")
    with (
        patch("urllib.request.urlopen", side_effect=[transient, Response()]) as opened,
        patch("time.sleep") as slept,
    ):
        result = transcribe_images([image], model="test", api_key="secret")
    assert result == {"version": 1, "blocks": []}
    assert opened.call_count == 2
    slept.assert_called_once_with(0.5)


def test_provider_does_not_retry_invalid_json(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    response = Response()
    response.read = lambda: b'{"choices": []}'
    with (
        patch("urllib.request.urlopen", return_value=response) as opened,
        pytest.raises(VisionError, match="invalid response"),
    ):
        transcribe_images([image], model="test", api_key="secret")
    assert opened.call_count == 1
