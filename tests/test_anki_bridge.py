import json
from unittest.mock import MagicMock, patch

import pytest

from pdf_school.bridges.anki_bridge import (
    check_ankiconnect_health,
    export_to_tsv,
    invoke_ankiconnect,
    load_questions,
    sync_to_ankiconnect,
)
from pdf_school.schemas import QBankQuestion


def _create_sample_question():
    return QBankQuestion(
        id="q_immuno_01",
        topic="Immunology",
        vignette="A patient with recurrent bacterial infections...",
        lead_in="What immunoglobulin is deficient?",
        options={"A": "IgA", "B": "IgG", "C": "IgM"},
        correct_key="B",
        educational_objective="IgG deficiency predisposes to encapsulated bacterial infections.",
        distractor_analysis={"A": "Mucosal", "B": "Correct", "C": "Primary response"},
    )


def test_export_to_tsv(tmp_path):
    tsv_out = tmp_path / "deck.tsv"
    q = _create_sample_question()
    count = export_to_tsv([q], str(tsv_out))

    assert count == 1
    assert tsv_out.exists()
    content = tsv_out.read_text(encoding="utf-8")
    assert "Immunology" in content
    assert "IgG deficiency" in content
    assert "\t" in content


def test_load_questions(tmp_path):
    qbank_file = tmp_path / "qbank.jsonl"
    q = _create_sample_question()
    with open(qbank_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(q.model_dump()) + "\n")
        f.write("\n")
        f.write("corrupted json\n")

    loaded = load_questions(str(qbank_file))
    assert len(loaded) == 1
    assert loaded[0].id == "q_immuno_01"

    # Nonexistent file returns empty
    assert load_questions(str(tmp_path / "nonexistent.jsonl")) == []


def test_check_ankiconnect_health():
    with patch("pdf_school.bridges.anki_bridge.invoke_ankiconnect", return_value=6):
        assert check_ankiconnect_health() is True

    with patch(
        "pdf_school.bridges.anki_bridge.invoke_ankiconnect",
        side_effect=Exception("Connection refused"),
    ):
        assert check_ankiconnect_health() is False


def test_sync_to_ankiconnect():
    q = _create_sample_question()
    with patch("pdf_school.bridges.anki_bridge.invoke_ankiconnect") as mock_invoke:
        mock_invoke.side_effect = [
            None,  # createDeck
            [123456789],  # addNotes returns note ID list
        ]
        count = sync_to_ankiconnect([q], deck_name="Test Deck")
        assert count == 1
        assert mock_invoke.call_count == 2


def test_invoke_ankiconnect():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"result": 6, "error": None}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = invoke_ankiconnect("version")
        assert res == 6

    # Error from AnkiConnect
    err_resp = MagicMock()
    err_resp.read.return_value = json.dumps({"result": None, "error": "Deck not found"}).encode(
        "utf-8"
    )
    err_resp.__enter__.return_value = err_resp

    with patch("urllib.request.urlopen", return_value=err_resp):
        with pytest.raises(RuntimeError, match="Deck not found"):
            invoke_ankiconnect("getDeck")
