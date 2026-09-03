from tools.qbank_forge import append_to_qbank, build_forge_prompt, validate_question_flaws
from tools.schemas import ContentChunk, ExamStyleProfile, QBankQuestion


def test_build_forge_prompt_track_b():
    chunk = ContentChunk(
        chunk_id="chunk_1",
        source_file="sources/test.pdf",
        page_start=1,
        page_end=2,
        text="Diuretics like furosemide inhibit the Na-K-2Cl cotransporter...",
    )
    prompt = build_forge_prompt(chunk, style_profile=None)
    assert "Pedagogical Mastery" in prompt
    assert "Refutational Feedback" in prompt
    assert "Contrasting Cases Matrix" in prompt


def test_validate_question_flaws_detects_all_of_the_above():
    flawed_q = {
        "options": {
            "A": "Lisinopril",
            "B": "Amlodipine",
            "C": "All of the above",
        },
        "correct_key": "C",
        "lead_in": "Which medication is indicated",  # Missing question mark
        "vignette": "A patient with hypertension...",
    }
    flaws = validate_question_flaws(flawed_q)
    assert any("question mark" in f for f in flaws)
    assert any("compromises discrimination" in f for f in flaws)


def test_append_to_qbank(tmp_path):
    qbank_file = tmp_path / "qbank.jsonl"
    q = QBankQuestion(
        id="q_renal_001",
        topic="Nephrology",
        subtopic="Diuretics",
        vignette="A 60-year-old male with CHF presents with acute pulmonary edema...",
        lead_in="Which of the following is the most appropriate first-line agent?",
        options={
            "A": "Furosemide",
            "B": "Hydrochlorothiazide",
            "C": "Spironolactone",
            "D": "Acetazolamide",
        },
        correct_key="A",
        educational_objective="Loop diuretics such as furosemide provide rapid symptom relief in acute pulmonary edema.",
        distractor_analysis={
            "A": "Correct: rapid preload reduction via venodilation and diuresis.",
            "B": "Incorrect: Thiazides are ineffective at low GFR and lack acute venodilatory effect.",
            "C": "Incorrect: Aldosterone antagonists have delayed onset.",
            "D": "Incorrect: Weak diuretic primarily used for altitude sickness or glaucoma.",
        },
    )
    res = append_to_qbank(q, str(qbank_file))
    assert res is True
    assert qbank_file.exists()

    # Second insert of same ID should be skipped
    res_duplicate = append_to_qbank(q, str(qbank_file))
    assert res_duplicate is False
