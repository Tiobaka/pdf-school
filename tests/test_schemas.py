import pytest
from tools.schemas import QBankQuestion, HistoryRecord


def test_qbank_question_validates_correct_key():
    # Valid question
    q = QBankQuestion(
        id="q_val_1",
        topic="Cardio",
        vignette="Vignette",
        lead_in="Lead in?",
        options={"A": "Alpha", "B": "Beta"},
        correct_key="A",
        educational_objective="Objective",
        distractor_analysis={"A": "ok", "B": "no"},
    )
    assert q.correct_key == "A"

    # Invalid question where correct_key is not in options
    with pytest.raises(ValueError, match="correct_key 'C' must be present in options"):
        QBankQuestion(
            id="q_val_2",
            topic="Cardio",
            vignette="Vignette",
            lead_in="Lead in?",
            options={"A": "Alpha", "B": "Beta"},
            correct_key="C",
            educational_objective="Objective",
            distractor_analysis={"A": "ok", "B": "no"},
        )


def test_history_record_flexible_fsrs_state():
    rec = HistoryRecord(
        question_id="q1",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        time_spent_seconds=12.5,
        fsrs_state={"state": 1, "reps": 3, "due": "2026-09-04T00:00:00Z"},
    )
    assert rec.fsrs_state["state"] == 1
    assert rec.fsrs_state["due"] == "2026-09-04T00:00:00Z"
