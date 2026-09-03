#!/usr/bin/env python3
"""
profile_exam.py - Analyzes past exams, quizzes, or professor sample questions
to synthesize an ExamStyleProfile for Track A question forging.
"""

import os
import sys
from pathlib import Path

# Automatically use local virtualenv interpreter if invoked with system python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
if _venv_python.exists() and sys.prefix != str(PROJECT_ROOT / ".venv"):
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)


import argparse
import json
import re
from typing import Dict, List, Optional

import pymupdf
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(PROJECT_ROOT))
from tools.schemas import ExamStyleProfile



DEFAULT_INPUT = str(PROJECT_ROOT / "sources" / "past_exams")
DEFAULT_OUTPUT = str(PROJECT_ROOT / "data" / "exam_style.json")

console = Console()


def extract_text_from_file(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        with pymupdf.open(str(file_path)) as doc:
            pages_text = [page.get_text() for page in doc]
        return "\n".join(pages_text)
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()



def analyze_exam_text(raw_text: str, profile_name: str = "custom_professor") -> ExamStyleProfile:
    # Pattern to find questions: lines starting with numbers like "1. ", "Question 1:", "Q1."
    question_split_pattern = re.compile(r"(?:^|\n)\s*(?:Question\s*)?(\d+)[\.\:\)]\s*", re.IGNORECASE)
    splits = question_split_pattern.split(raw_text)
    
    questions_raw: List[str] = []
    if len(splits) > 1:
        # splits: [preamble, q_num1, q_text1, q_num2, q_text2, ...]
        for i in range(2, len(splits), 2):
            questions_raw.append(splits[i].strip())
    else:
        # Fallback: split by double newlines
        questions_raw = [block.strip() for block in raw_text.split("\n\n") if len(block.strip()) > 30]

    total_detected = len(questions_raw)
    if total_detected == 0:
        return ExamStyleProfile(
            style_name=profile_name,
            stem_type="short_vignette",
            option_count=4,
            allows_negative_stems=False,
            allows_multiple_select=False,
            focus_areas=["general_curriculum"],
            exemplars=[],
        )

    stem_word_counts: List[int] = []
    option_counts_list: List[int] = []
    negative_stem_count = 0
    multiple_select_count = 0
    exemplars: List[Dict[str, str]] = []

    # Regex for options (A., B., C., D., E. or A), B))
    option_regex = re.compile(r"(?:^|\n)\s*([A-Ea-e])[\.\)]\s*(.+)")
    negative_pattern = re.compile(r"\b(NOT|EXCEPT|LEAST|FALSE|INCORRECT)\b")

    for q in questions_raw:
        # Find options in question
        options = option_regex.findall(q)
        if options:
            option_counts_list.append(len(options))
            # Stem is everything before the first option
            first_opt_match = option_regex.search(q)
            stem = q[:first_opt_match.start()].strip() if first_opt_match else q
        else:
            stem = q

        stem_words = stem.split()
        stem_word_counts.append(len(stem_words))

        if negative_pattern.search(stem):
            negative_stem_count += 1

        if re.search(r"\b(both|all of the above|none of the above|I and II|A and B)\b", q, re.IGNORECASE):
            multiple_select_count += 1

        # Keep up to 3 clean exemplars
        if len(exemplars) < 3 and len(stem_words) >= 5 and options:
            exemplar_dict = {
                "stem": stem,
                "options": "\n".join([f"{opt[0].upper()}) {opt[1].strip()}" for opt in options])
            }
            exemplars.append(exemplar_dict)

    avg_stem_len = sum(stem_word_counts) / len(stem_word_counts) if stem_word_counts else 30
    avg_opt_count = round(sum(option_counts_list) / len(option_counts_list)) if option_counts_list else 4

    if avg_stem_len < 25:
        stem_type = "direct_recall"
    elif avg_stem_len < 80:
        stem_type = "short_vignette"
    else:
        stem_type = "long_clinical_case"

    allows_negative = (negative_stem_count / total_detected) > 0.1
    allows_multiselect = (multiple_select_count / total_detected) > 0.1

    return ExamStyleProfile(
        style_name=profile_name,
        stem_type=stem_type,
        option_count=max(4, min(5, avg_opt_count)),
        allows_negative_stems=allows_negative,
        allows_multiple_select=allows_multiselect,
        focus_areas=[f"avg_stem_length_{int(avg_stem_len)}_words"],
        exemplars=exemplars,
    )


def profile_exams(input_dir_or_file: str, output_file: str = "data/exam_style.json") -> Optional[ExamStyleProfile]:
    path = Path(input_dir_or_file)
    if not path.exists():
        console.print(f"[yellow]⚠️ Target path '{input_dir_or_file}' does not exist.[/yellow]")
        return None

    all_text = []
    if path.is_file():
        all_text.append(extract_text_from_file(path))
        profile_name = path.stem
    else:
        files = list(path.glob("*.*"))
        valid_files = [f for f in files if f.suffix.lower() in [".pdf", ".txt", ".md", ".json"]]
        if not valid_files:
            console.print(f"[yellow]⚠️ No past exam files (.pdf, .txt, .md) found in '{input_dir_or_file}'.[/yellow]")
            return None
        for f in valid_files:
            all_text.append(extract_text_from_file(f))
        profile_name = "course_professor_profile"

    combined_text = "\n\n".join(all_text)
    profile = analyze_exam_text(combined_text, profile_name=profile_name)

    out_p = Path(output_file)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)

    return profile


def display_profile(profile: ExamStyleProfile, dest_file: str):
    table = Table(title="🎓 Professor Exam Style Profile (Track A Active)", show_header=True, header_style="bold magenta")
    table.add_column("Attribute", style="cyan")
    table.add_column("Detected Pattern", style="green")

    table.add_row("Profile Name", profile.style_name)
    table.add_row("Question Stem Style", profile.stem_type)
    table.add_row("Standard Option Count", f"{profile.option_count} choices")
    table.add_row("Negative Stems (EXCEPT/NOT)", "Yes (Frequently used)" if profile.allows_negative_stems else "No / Minimal")
    table.add_row("Multiple Selection / True-False", "Yes (Detected)" if profile.allows_multiple_select else "No / Standard MCQ")
    table.add_row("Extracted Exemplars", f"{len(profile.exemplars)} sample questions captured")

    console.print(Panel(table, title="[bold blue]PDF-School Exam Profiler[/bold blue]", expand=False))
    console.print(f"💾 Saved profile configuration to: [bold underline]{dest_file}[/bold underline]\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze past exams and generate an ExamStyleProfile for Track A")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Directory or file containing past exams")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Destination JSON path for the profile")


    args = parser.parse_args()
    profile = profile_exams(args.input, args.output)
    if profile:
        display_profile(profile, args.output)
    else:
        console.print("[blue]ℹ️ No exam profile generated. Track B (Pedagogical Mastery Mode) will be used by default.[/blue]")


if __name__ == "__main__":
    main()
