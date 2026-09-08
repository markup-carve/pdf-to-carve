import io

from pdf_to_carve.correct import correct_interactively, needs_review
from pdf_to_carve.model import HUMAN_CORRECTED_WARNING, Document


def uncertain_document() -> Document:
    return Document.from_json(
        {
            "version": 1,
            "blocks": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Old"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Certain"}]},
            ],
            "provenance": [
                {"block": 0, "page": 1, "confidence": 0.6, "warnings": ["check text"]},
                {"block": 1, "page": 1, "confidence": 0.99},
            ],
        }
    )


def test_interactive_correction_reprompts_until_replacement_validates() -> None:
    answers = io.StringIO(
        '{"type":"unknown"}\n{"type":"paragraph","content":[{"type":"text","text":"New"}]}\n'
    )
    transcript = io.StringIO()
    corrected = correct_interactively(
        uncertain_document(), input_stream=answers, output_stream=transcript
    )
    assert corrected.blocks[0].data["content"][0].text == "New"
    assert corrected.provenance[0].confidence == 0.6
    assert HUMAN_CORRECTED_WARNING in corrected.provenance[0].warnings
    assert not needs_review(corrected.provenance[0], 0.85)
    assert "invalid replacement" in transcript.getvalue()
    assert transcript.getvalue().count("replacement JSON") == 2
    assert '\n  "type"' not in transcript.getvalue()


def test_interactive_enter_keeps_block_queued() -> None:
    corrected = correct_interactively(
        uncertain_document(), input_stream=io.StringIO("\n"), output_stream=io.StringIO()
    )
    assert corrected.blocks == uncertain_document().blocks
    assert needs_review(corrected.provenance[0], 0.85)


def test_interactive_eof_stops_instead_of_appearing_to_review_every_block() -> None:
    document = Document.from_json(
        {
            "version": 1,
            "blocks": [
                {"type": "paragraph", "content": []},
                {"type": "paragraph", "content": []},
            ],
            "provenance": [
                {"block": 0, "page": 1, "confidence": 0.5},
                {"block": 1, "page": 2, "confidence": 0.5},
            ],
        }
    )
    transcript = io.StringIO()
    assert (
        correct_interactively(document, input_stream=io.StringIO(""), output_stream=transcript)
        == document
    )
    assert transcript.getvalue().count("replacement JSON") == 1
    assert "input closed" in transcript.getvalue()
