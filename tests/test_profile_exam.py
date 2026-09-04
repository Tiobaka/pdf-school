from pdf_school.engine.profile_exam import analyze_exam_text, display_profile, profile_exams


def test_analyze_exam_text_short_recall():
    sample_text = """
    1. Which of the following enzymes is the rate-limiting step in glycolysis?
    A. Hexokinase
    B. Phosphofructokinase-1
    C. Pyruvate kinase
    D. Aldolase

    2. All of the following are glycogen storage diseases EXCEPT:
    A. Von Gierke disease
    B. Pompe disease
    C. Tay-Sachs disease
    D. McArdle disease
    """
    profile = analyze_exam_text(sample_text, profile_name="biochem_quiz")

    assert profile.style_name == "biochem_quiz"
    assert profile.option_count == 4
    assert profile.stem_type == "direct_recall"
    assert profile.allows_negative_stems is True
    assert len(profile.exemplars) == 2


def test_profile_exams_file(tmp_path):
    exam_file = tmp_path / "pharmacology_midterm.txt"
    exam_file.write_text(
        """
    1. A 55-year-old male with chronic hypertension presents for routine follow-up. Blood pressure is 150/92 mmHg.
    Which of the following first-line medications is most appropriate?
    A. Lisinopril
    B. Amlodipine
    C. Hydrochlorothiazide
    D. Metoprolol
    E. Spironolactone
    """,
        encoding="utf-8",
    )

    out_json = tmp_path / "style.json"
    profile = profile_exams(str(exam_file), str(out_json))

    assert profile is not None
    assert profile.option_count == 5
    assert out_json.exists()


def test_display_profile_and_dir(tmp_path):
    exam_dir = tmp_path / "exams"
    exam_dir.mkdir()
    f1 = exam_dir / "exam1.txt"
    f1.write_text(
        "1. Question?\nA. Opt 1\nB. Opt 2\nC. Opt 3\nD. Opt 4\nE. Opt 5\n", encoding="utf-8"
    )

    out_json = tmp_path / "dir_style.json"
    prof = profile_exams(str(exam_dir), str(out_json))
    assert prof is not None
    assert prof.option_count == 5

    # Test display_profile does not throw
    display_profile(prof, str(out_json))
