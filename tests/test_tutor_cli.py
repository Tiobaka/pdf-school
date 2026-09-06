import json

from pdf_school.schemas import HistoryRecord, QBankQuestion
from pdf_school.tui.cli_runner import load_qbank, log_history


def test_load_qbank(tmp_path):
    qbank_file = tmp_path / "test_qbank.jsonl"
    q = QBankQuestion(
        id="q_cardio_101",
        topic="Cardiology",
        subtopic="Arrhythmias",
        vignette="A 45-year-old female presents with episodic rapid heart rate...",
        lead_in="Which ECG finding confirms the diagnosis?",
        options={"A": "Delta wave", "B": "ST elevation", "C": "Prolonged PR", "D": "Tall T waves"},
        correct_key="A",
        educational_objective="Delta waves indicate pre-excitation in Wolff-Parkinson-White syndrome.",
        distractor_analysis={
            "A": "Correct",
            "B": "STEMI",
            "C": "First degree AV block",
            "D": "Hyperkalemia",
        },
    )
    with open(qbank_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(q.model_dump()) + "\n")

    loaded = load_qbank(str(qbank_file))
    assert len(loaded) == 1
    assert loaded[0].id == "q_cardio_101"
    assert loaded[0].topic == "Cardiology"


def test_log_history(tmp_path):
    hist_file = tmp_path / "history.jsonl"
    record = HistoryRecord(
        question_id="q_cardio_101",
        selected_key="B",
        correct_key="A",
        is_correct=False,
        time_spent_seconds=42.5,
        confidence_rating="educated_guess",
        switched_answer=True,
        original_selection="C",
        error_category="misconception",
        user_note="Confused pre-excitation with ischemia",
    )
    log_history(record, str(hist_file))

    assert hist_file.exists()
    with open(hist_file, encoding="utf-8") as f:
        data = json.loads(f.readline())
    assert data["question_id"] == "q_cardio_101"
    assert data["is_correct"] is False
    assert data["error_category"] == "misconception"
    assert data["switched_answer"] is True


def test_cli_runner_argument_parsing(monkeypatch):
    from pdf_school.tui.cli_runner import main as cli_main

    # Test that --help or standard parser works without AttributeError
    monkeypatch.setattr("sys.argv", ["tutor_cli.py", "--help"])
    import pytest

    with pytest.raises(SystemExit) as exc_info:
        cli_main()
    assert exc_info.value.code == 0
