import json

from pdf_school.engine.roadmap import (
    calculate_progress_and_debt,
    get_actual_vignettes_completed_by_date,
    load_roadmap,
    print_status_view,
    print_today_view,
    rebalance_schedule,
    save_roadmap,
)


def test_load_roadmap():
    roadmap = load_roadmap()
    assert roadmap["exam_target"] == "Final de Clínica Médica II"
    assert len(roadmap["days"]) == 41
    assert len(roadmap["milestones"]) == 4


def test_calculate_progress_and_debt():
    sample_roadmap = {
        "days": [
            {
                "date": "2026-09-01",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-02",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-03",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-04",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-05",
                "is_rest": True,
                "target_vignettes": 0,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-06",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
        ]
    }
    # Simulate user did 10 questions on Sept 1 and 0 on Sept 2
    history_counts = {"2026-09-01": 10}

    # As of Sept 3: planned past = 18 (day 1) + 18 (day 2) = 36. Completed = 10. Debt = 26.
    planned, completed, debt, past_days, future_days = calculate_progress_and_debt(
        sample_roadmap, "2026-09-03", history_counts=history_counts
    )

    assert planned == 36
    assert completed == 10
    assert debt == 26
    assert len(future_days) == 2  # Sept 4, Sept 6 (Sept 5 is rest day)


def test_rebalance_schedule_deterministic():
    sample_roadmap = {
        "days": [
            {
                "date": "2026-09-01",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-02",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-03",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-04",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-05",
                "is_rest": True,
                "target_vignettes": 0,
                "completed_vignettes": 0,
            },
            {
                "date": "2026-09-06",
                "is_rest": False,
                "target_vignettes": 18,
                "completed_vignettes": 0,
            },
        ]
    }
    # User completed 0 questions on Day 1 and Day 2 -> debt = 36
    updated_rm, debt, changes = rebalance_schedule(
        sample_roadmap, "2026-09-03", history_counts={}, spread_across_days=2
    )

    assert debt == 36
    assert len(changes) == 2
    # Sept 4 and Sept 6 should each receive 18 extra questions (36 / 2 = 18)
    assert changes[0][0] == "2026-09-04"
    assert changes[0][2] == 36  # 18 + 18
    assert changes[1][0] == "2026-09-06"
    assert changes[1][2] == 36  # 18 + 18

    # Rest day Sept 5 was untouched!
    sept_5 = [d for d in updated_rm["days"] if d["date"] == "2026-09-05"][0]
    assert sept_5["target_vignettes"] == 0


def test_save_and_history_counts(tmp_path):
    rm_path = tmp_path / "roadmap.json"
    data = {"exam_target": "Test Exam", "days": []}
    save_roadmap(data, rm_path)
    assert rm_path.exists()

    hist_path = tmp_path / "history.jsonl"
    with open(hist_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": "2026-09-04T10:00:00Z", "question_id": "q1"}) + "\n")
        f.write(json.dumps({"timestamp": "2026-09-04T11:00:00Z", "question_id": "q2"}) + "\n")
        f.write("\n")
        f.write("corrupted line\n")

    counts = get_actual_vignettes_completed_by_date(hist_path)
    assert counts.get("2026-09-04") == 2


def test_print_views():
    # Should render rich cards without raising errors
    print_today_view("2026-09-04")
    print_today_view("2099-01-01")  # day outside roadmap
    print_status_view("2026-09-04")
