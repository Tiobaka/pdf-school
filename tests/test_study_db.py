import json

from pdf_school.bridges.study_db import (
    display_reports,
    get_calibration_report,
    get_db_connection,
    get_error_taxonomy_report,
    get_mastery_report,
    get_time_analysis,
    get_weakness_queue,
    sync_db,
)
from pdf_school.schemas import HistoryRecord, QBankQuestion


def create_sample_dataset(tmp_path):
    qbank_path = tmp_path / "qbank.jsonl"
    history_path = tmp_path / "history.jsonl"
    db_path = tmp_path / "study.db"

    q1 = QBankQuestion(
        id="q_renal_01",
        topic="Renal",
        subtopic="Diuretics",
        difficulty_hammer=3,
        vignette="CHF patient with acute edema...",
        lead_in="Best drug?",
        options={"A": "Furosemide", "B": "HCTZ"},
        correct_key="A",
        educational_objective="Loop diuretics are first-line for acute pulmonary edema.",
        distractor_analysis={"A": "Correct", "B": "Too slow"},
    )
    q2 = QBankQuestion(
        id="q_cardio_01",
        topic="Cardiology",
        subtopic="Arrhythmias",
        difficulty_hammer=4,
        vignette="Patient on antiarrhythmic with lung fibrosis...",
        lead_in="Causative drug?",
        options={"A": "Amiodarone", "B": "Metoprolol"},
        correct_key="A",
        educational_objective="Amiodarone causes pulmonary fibrosis.",
        distractor_analysis={"A": "Correct", "B": "Beta blocker"},
    )

    with open(qbank_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(q1.model_dump()) + "\n")
        f.write(json.dumps(q2.model_dump()) + "\n")

    # History:
    # 1. q_renal_01 answered incorrectly with 'certain' confidence (Misconception / Dunning-Kruger blunder)
    h1 = HistoryRecord(
        timestamp="2026-09-01T10:00:00Z",
        question_id="q_renal_01",
        selected_key="B",
        correct_key="A",
        is_correct=False,
        time_spent_seconds=45.0,
        confidence_rating="certain",
        error_category="misconception",
    )
    # 2. q_cardio_01 answered correctly with 'educated_guess', switched from B to A
    h2 = HistoryRecord(
        timestamp="2026-09-02T10:00:00Z",
        question_id="q_cardio_01",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        time_spent_seconds=20.0,
        confidence_rating="educated_guess",
        switched_answer=True,
        original_selection="B",
    )

    with open(history_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(h1.model_dump()) + "\n")
        f.write(json.dumps(h2.model_dump()) + "\n")

    return db_path, qbank_path, history_path


def test_study_db_sync_idempotency_and_soft_delete(tmp_path):
    db_path, qbank_path, history_path = create_sample_dataset(tmp_path)

    # First sync
    counts1 = sync_db(db_path, qbank_path, history_path, force=True)
    assert counts1["questions"] == 2
    assert counts1["history"] == 2

    # Second sync without changes should be an early exit
    counts2 = sync_db(db_path, qbank_path, history_path, force=False)
    assert counts2["questions"] == 0
    assert counts2["history"] == 0

    # Verify rows in database
    conn = get_db_connection(db_path)
    q_rows = conn.execute("SELECT * FROM questions WHERE is_active = 1").fetchall()
    assert len(q_rows) == 2
    h_rows = conn.execute("SELECT * FROM history").fetchall()
    assert len(h_rows) == 2

    # Test soft-delete: remove q2 from qbank.jsonl and force sync
    with open(qbank_path, encoding="utf-8") as f:
        q1_only = [json.loads(line) for line in f if "q_renal_01" in line]
    with open(qbank_path, "w", encoding="utf-8") as f:
        for q in q1_only:
            f.write(json.dumps(q) + "\n")

    sync_db(db_path, qbank_path, history_path, force=True)
    active_rows = conn.execute("SELECT * FROM questions WHERE is_active = 1").fetchall()
    assert len(active_rows) == 1
    assert active_rows[0]["id"] == "q_renal_01"

    deleted_rows = conn.execute("SELECT * FROM questions WHERE is_active = 0").fetchall()
    assert len(deleted_rows) == 1
    assert deleted_rows[0]["id"] == "q_cardio_01"
    conn.close()


def test_analytical_reports(tmp_path):
    db_path, qbank_path, history_path = create_sample_dataset(tmp_path)
    sync_db(db_path, qbank_path, history_path, force=True)
    conn = get_db_connection(db_path)

    # 1. Mastery Report with substring topic search
    mastery_all = get_mastery_report(conn)
    assert len(mastery_all) == 2

    mastery_cardio = get_mastery_report(conn, topic="cardio")
    assert len(mastery_cardio) == 1
    assert mastery_cardio[0]["topic"] == "Cardiology"
    assert mastery_cardio[0]["current_mastery_pct"] == 100.0

    # 2. Metacognitive Calibration Report
    calib = get_calibration_report(conn)
    certain_c = next(c for c in calib if c["confidence_rating"] == "certain")
    assert certain_c["dunning_kruger_blunders"] == 1
    assert certain_c["actual_accuracy_pct"] == 0.0

    # 3. Error Taxonomy Report
    errors = get_error_taxonomy_report(conn)
    assert len(errors) == 1
    assert errors[0]["topic"] == "Renal"
    assert errors[0]["error_category"] == "misconception"
    assert errors[0]["count"] == 1

    # 4. Time and Switching Analysis
    time_stats = get_time_analysis(conn)
    assert len(time_stats) == 2
    switched_row = next(t for t in time_stats if t["switched_answer"] == 1)
    assert switched_row["count"] == 1
    assert switched_row["accuracy_pct"] == 100.0

    conn.close()


def test_adaptive_weakness_queue_prioritization_and_substring(tmp_path):
    db_path, qbank_path, history_path = create_sample_dataset(tmp_path)

    # q_renal_01 had an entrenched misconception with 'certain' confidence
    # It should be returned as #1 priority in weakness queue!
    queue = get_weakness_queue(db_path, qbank_path, history_path, limit=5)
    assert len(queue) >= 1
    assert queue[0].id == "q_renal_01"
    assert queue[0].topic == "Renal"

    # Substring topic filter "ren" matches "Renal"
    queue_ren = get_weakness_queue(db_path, qbank_path, history_path, limit=5, topic="ren")
    assert len(queue_ren) == 1
    assert queue_ren[0].id == "q_renal_01"


def test_study_db_resilience_to_missing_and_corrupt_files(tmp_path):
    db_path = tmp_path / "study.db"
    qb_missing = tmp_path / "nonexistent_qbank.jsonl"
    hist_corrupt = tmp_path / "corrupt_history.jsonl"

    with open(hist_corrupt, "w", encoding="utf-8") as f:
        f.write("NOT_A_JSON_STRING\n")
        f.write("{'bad': 'quotes'}\n")
        f.write("\n")

    # Sync should succeed gracefully without crashing
    counts = sync_db(db_path, qb_missing, hist_corrupt, force=True)
    assert counts["questions"] == 0
    assert counts["history"] == 0

    # Display reports on empty db should not throw
    conn = get_db_connection(db_path)
    display_reports(conn)
    conn.close()


def test_display_reports_with_data(tmp_path):
    db_path, qbank_path, history_path = create_sample_dataset(tmp_path)
    sync_db(db_path, qbank_path, history_path)
    conn = get_db_connection(db_path)
    # Ensure all tables render without exceptions
    display_reports(conn, topic="Renal")
    display_reports(conn, topic=None)
    conn.close()
