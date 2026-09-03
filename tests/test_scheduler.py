import json
from datetime import datetime, timezone
from pathlib import Path
from tools.schemas import DailySchedule, HistoryRecord, QBankQuestion
from tools.scheduler import compute_question_fsrs_states, generate_daily_schedule


def test_fsrs_history_computation(tmp_path):
    hist_file = tmp_path / "history.jsonl"
    rec1 = HistoryRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        question_id="q_renal_001",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        time_spent_seconds=30.0,
        confidence_rating="certain",
    )
    with open(hist_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec1.model_dump()) + "\n")

    cards = compute_question_fsrs_states(str(hist_file))
    assert "q_renal_001" in cards
    assert cards["q_renal_001"].stability > 0


def test_generate_daily_schedule(tmp_path):
    qbank_file = tmp_path / "qbank.jsonl"
    hist_file = tmp_path / "history.jsonl"
    sched_file = tmp_path / "schedule.json"

    # Add two questions
    q1 = QBankQuestion(
        id="q1",
        topic="Cardiology",
        vignette="Vignette 1",
        lead_in="Question 1?",
        options={"A": "1", "B": "2"},
        correct_key="A",
        educational_objective="Obj 1",
        distractor_analysis={"A": "ok", "B": "no"},
    )
    q2 = QBankQuestion(
        id="q2",
        topic="Cardiology",
        vignette="Vignette 2",
        lead_in="Question 2?",
        options={"A": "1", "B": "2"},
        correct_key="A",
        educational_objective="Obj 2",
        distractor_analysis={"A": "ok", "B": "no"},
    )
    with open(qbank_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(q1.model_dump()) + "\n")
        f.write(json.dumps(q2.model_dump()) + "\n")

    schedule = generate_daily_schedule(
        qbank_path=str(qbank_file),
        history_path=str(hist_file),
        output_path=str(sched_file),
        max_new=10,
    )

    assert len(schedule.new_questions) == 2
    assert "q1" in schedule.new_questions
    assert "q2" in schedule.new_questions
    assert sched_file.exists()
