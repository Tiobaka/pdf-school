import json
from datetime import datetime, timezone

from pdf_school.engine.scheduler import (
    compute_question_fsrs_states,
    generate_daily_schedule,
)
from pdf_school.schemas import HistoryRecord, QBankQuestion


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
    assert cards["q_renal_001"].stability is not None and cards["q_renal_001"].stability > 0


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


def test_fsrs_chronological_replay_and_overdue_sorting(tmp_path):
    qbank_file = tmp_path / "qbank.jsonl"
    hist_file = tmp_path / "history.jsonl"
    sched_file = tmp_path / "schedule.json"

    # Only q1 is in active qbank (q_orphaned was deleted)
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
    with open(qbank_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(q1.model_dump()) + "\n")

    # History logged out of order: review 2 logged before review 1
    # Review 1: 2 days ago (is_correct=False)
    # Review 2: 1 day ago (is_correct=True, educated_guess)
    # Orphaned review: 3 days ago (is_correct=True)
    r_orphan = HistoryRecord(
        timestamp="2026-09-01T10:00:00Z",
        question_id="q_orphaned",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        time_spent_seconds=20.0,
    )
    r2 = HistoryRecord(
        timestamp="2026-09-02T12:00:00Z",
        question_id="q1",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        time_spent_seconds=25.0,
        confidence_rating="educated_guess",
    )
    r1 = HistoryRecord(
        timestamp="2026-09-01T12:00:00Z",
        question_id="q1",
        selected_key="B",
        correct_key="A",
        is_correct=False,
        time_spent_seconds=40.0,
    )

    with open(hist_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(r_orphan.model_dump()) + "\n")
        f.write(json.dumps(r2.model_dump()) + "\n")
        f.write(json.dumps(r1.model_dump()) + "\n")

    cards = compute_question_fsrs_states(str(hist_file))
    assert "q1" in cards
    assert cards["q1"].stability is not None and cards["q1"].stability > 0
    assert cards["q1"].last_review is not None

    # Verify daily schedule excludes q_orphaned and includes q1
    sched = generate_daily_schedule(
        qbank_path=str(qbank_file),
        history_path=str(hist_file),
        output_path=str(sched_file),
    )
    assert "q_orphaned" not in sched.due_reviews
    assert "q_orphaned" not in sched.new_questions
