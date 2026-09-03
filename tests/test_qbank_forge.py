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


def test_validate_question_flaws_distinguishes_vignette_from_leadin():
    # Vignette contains "not in acute distress" and "except for mild bibasilar crackles"
    # This should NOT be flagged as negative stem flaw because lead-in is positive
    valid_q = {
        "options": {"A": "A", "B": "B"},
        "correct_key": "A",
        "lead_in": "Which of the following is the most likely diagnosis?",
        "vignette": "A 45-year-old male is not in acute distress. Examination is unremarkable except for mild edema.",
        "distractor_analysis": {"A": "ok", "B": "no"},
    }
    flaws = validate_question_flaws(valid_q)
    assert not any("negative stem" in f for f in flaws)

    # But if lead_in has negative phrasing, it MUST be flagged
    negative_lead_in_q = {
        "options": {"A": "A", "B": "B"},
        "correct_key": "A",
        "lead_in": "Which of the following is NOT an appropriate therapy?",
        "vignette": "A 45-year-old male presents with palpitations.",
        "distractor_analysis": {"A": "ok", "B": "no"},
    }
    flaws_neg = validate_question_flaws(negative_lead_in_q)
    assert any("negative stem" in f for f in flaws_neg)



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


from unittest.mock import patch
import json


def test_auto_forge_questions(tmp_path):
    chunks_file = tmp_path / "chunks.jsonl"
    qbank_file = tmp_path / "qbank.jsonl"

    chunk = ContentChunk(
        chunk_id="chunk_test",
        source_file="sources/test.pdf",
        page_start=1,
        page_end=1,
        text="Amiodarone is a class III antiarrhythmic...",
    )
    chunks_file.write_text(json.dumps(chunk.model_dump()) + "\n", encoding="utf-8")

    mock_response = {
        "id": "q_amio_01",
        "topic": "Cardiology",
        "subtopic": "Antiarrhythmics",
        "source_ref": {"chunk_id": "chunk_test", "source_file": "sources/test.pdf", "page": "1"},
        "difficulty_hammer": 3,
        "cognitive_level": "2nd_order_application",
        "figures": [],
        "vignette": "A 58-year-old male on chronic antiarrhythmic therapy develops pulmonary fibrosis...",
        "lead_in": "Which medication is most likely responsible?",
        "options": {"A": "Amiodarone", "B": "Flecainide", "C": "Metoprolol", "D": "Diltiazem"},
        "correct_key": "A",
        "educational_objective": "Amiodarone causes pulmonary toxicity characterized by pulmonary fibrosis.",
        "distractor_analysis": {
            "A": "Correct: Causes pulmonary fibrosis.",
            "B": "Incorrect: Class IC proarrhythmic.",
            "C": "Incorrect: Beta-blocker.",
            "D": "Incorrect: Calcium channel blocker.",
        },
    }

    with patch("tools.qbank_forge.generate_structured_json", return_value=mock_response):
        from tools.qbank_forge import auto_forge_questions
        success = auto_forge_questions(
            chunk_file=str(chunks_file),
            count=1,
            profile_path=str(tmp_path / "nonexistent.json"),
            qbank_path=str(qbank_file),
        )
        assert success == 1
        assert qbank_file.exists()

