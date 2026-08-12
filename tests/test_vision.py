import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from pdf_to_carve.vision import VisionError, transcribe_images, transcribe_images_codex


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int = -1):
        payload = json.dumps(
            {"choices": [{"message": {"content": '{"version":1,"blocks":[]}'}}]}
        ).encode()
        return payload if size < 0 else payload[:size]


def test_provider_builds_openai_compatible_json_request(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    with patch("urllib.request.urlopen", return_value=Response()) as opened:
        assert transcribe_images(
            [image], model="vision-test", api_key="secret", context="trusted OCR hint"
        ) == {
            "version": 1,
            "blocks": [],
        }
    request = opened.call_args.args[0]
    body = json.loads(request.data)
    assert request.headers["Authorization"] == "Bearer secret"
    assert body["model"] == "vision-test"
    assert body["response_format"] == {"type": "json_object"}
    assert "trusted OCR hint" in body["messages"][1]["content"][0]["text"]
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
    response.read = lambda _size=-1: b'{"choices": []}'
    with (
        patch("urllib.request.urlopen", return_value=response) as opened,
        pytest.raises(VisionError, match="invalid response"),
    ):
        transcribe_images([image], model="test", api_key="secret")
    assert opened.call_count == 1


def test_provider_rejects_oversized_response(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    response = Response()
    response.read = lambda size=-1: b"x" * size
    with (
        patch("urllib.request.urlopen", return_value=response),
        patch("pdf_to_carve.vision.MAX_RESPONSE_BYTES", 20),
        pytest.raises(VisionError, match="exceeded"),
    ):
        transcribe_images([image], model="test", api_key="secret")


def test_codex_cli_provider_is_read_only_ephemeral_and_returns_json(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")

    def run(command, **kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text('{"version":1,"blocks":[]}')
        assert command[0] == "/bin/codex"
        assert "--ephemeral" in command
        assert "--ignore-user-config" in command
        assert command[command.index("--sandbox") + 1] == "read-only"
        assert str(image.resolve()) in command
        assert "evidence" in kwargs["input"]
        return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    with (
        patch("pdf_to_carve.vision.shutil.which", return_value="/bin/codex"),
        patch("pdf_to_carve.vision.subprocess.run", side_effect=run),
    ):
        assert transcribe_images_codex([image], model="test-model", context="evidence") == {
            "version": 1,
            "blocks": [],
        }


def test_codex_cli_provider_requires_executable(tmp_path: Path) -> None:
    with (
        patch("pdf_to_carve.vision.shutil.which", return_value=None),
        pytest.raises(VisionError, match="not found"),
    ):
        transcribe_images_codex([tmp_path / "page.png"], model="test")
