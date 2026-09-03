#!/usr/bin/env python3
"""
qbank_forge.py - Question forging engine supporting Track A (Professor Style)
and Track B (Pedagogical Mastery), schema validation, and NBME item flaw linting.
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
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(PROJECT_ROOT))
from tools.schemas import ContentChunk, ExamStyleProfile, QBankQuestion



console = Console()


def build_forge_prompt(chunk: ContentChunk, style_profile: Optional[ExamStyleProfile] = None) -> str:
    """
    Constructs a high-precision prompt for LLM or Antigravity subagent.
    """
    figures_info = f"Attached Figures: {', '.join(chunk.figures)}" if chunk.figures else "No figures attached."
    source_context = f"Source: {chunk.source_file} (Pages {chunk.page_start}-{chunk.page_end})\nSection: {chunk.section_title or 'General'}\n{figures_info}\n\nContent Chunk:\n\"\"\"\n{chunk.text}\n\"\"\""

    if style_profile and style_profile.style_name != "default_mastery":
        # Track A: Professor Style Alignment
        exemplar_text = ""
        if style_profile.exemplars:
            exemplar_text = "\n\n### Exemplars of Professor's Style:\n"
            for i, ex in enumerate(style_profile.exemplars, 1):
                exemplar_text += f"\nExample {i}:\n{ex.get('stem')}\n{ex.get('options')}\n"

        prompt = f"""You are a specialized academic exam writer. Your goal is to forge an exam question based ON THE PROVIDED SOURCE CHUNK, strictly adhering to the professor's exam style.

{source_context}

### Target Exam Profile (Track A - Professor Alignment):
- Question Stem Style: {style_profile.stem_type}
- Option Count: {style_profile.option_count} options (A through {chr(64 + style_profile.option_count)})
- Negative Stems (e.g. EXCEPT/NOT): {'Permitted if characteristic' if style_profile.allows_negative_stems else 'Avoid'}
- Multiple Selection / Composite: {'Permitted if characteristic' if style_profile.allows_multiple_select else 'Avoid'}
{exemplar_text}

Output MUST be a single valid JSON object adhering to this schema:
{{
  "id": "deterministic_unique_string",
  "topic": "Subject topic",
  "subtopic": "Subtopic",
  "source_ref": {{"chunk_id": "{chunk.chunk_id}", "source_file": "{chunk.source_file}", "page": "{chunk.page_start}"}},
  "difficulty_hammer": 3,
  "cognitive_level": "2nd_order_application",
  "figures": {json.dumps(chunk.figures)},
  "vignette": "Question scenario or stem",
  "lead_in": "Interrogative prompt ending in a question mark?",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct_key": "A",
  "educational_objective": "1-sentence high-yield takeaway",
  "distractor_analysis": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "refutational_hints": {{"B": "Why student might pick B and why it fails here...", "C": "...", "D": "..."}},
  "comparison_table": "| Parameter | Correct Option | Main Distractor |\\n|---|---|---|\\n..."
}}
"""
    else:
        # Track B: Pedagogical Mastery Mode (Cognitive Science)
        prompt = f"""You are an elite medical and academic educator trained in cognitive psychology and NBME item-writing standards. Your goal is to forge a LEARNING-OPTIMIZED question from the provided source chunk.

{source_context}

### Cognitive Science Requirements (Track B - Pedagogical Mastery):
1. **Desirable Difficulty & 2nd-Order Reasoning**: Present a clinical/practical scenario requiring multi-step synthesis (Clinical Clues -> Pathophysiology/Mechanism -> Management/Outcome). Avoid shallow 1st-order factual recall.
2. **Competitive Lures (Differential Diagnoses)**: Distractors must be plausible alternatives or common clinical misconceptions from the same conceptual family (The Little & Bjork Effect).
3. **Refutational Feedback**: For every incorrect option, provide an explicit refutation that identifies WHY a student would be tempted to pick it and the exact reason it is invalid in this case.
4. **Contrasting Cases Matrix**: Provide a clean Markdown comparison table highlighting key discriminators between the correct answer and the closest distractor.
5. **Takeaway Anchor**: Summarize the essential high-yield principle in exactly 1 crisp sentence.
6. **NBME Standards**: Avoid negative stems ('EXCEPT/NOT'), avoid 'All/None of the above', keep distractor lengths homogeneous.

Output MUST be a single valid JSON object adhering to this schema:
{{
  "id": "deterministic_unique_string",
  "topic": "Subject topic",
  "subtopic": "Subtopic",
  "source_ref": {{"chunk_id": "{chunk.chunk_id}", "source_file": "{chunk.source_file}", "page": "{chunk.page_start}"}},
  "difficulty_hammer": 3,
  "cognitive_level": "2nd_order_application",
  "figures": {json.dumps(chunk.figures)},
  "vignette": "Rich patient or practical scenario",
  "lead_in": "Which of the following is the most appropriate next step in management?",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
  "correct_key": "A",
  "educational_objective": "1-sentence high-yield takeaway",
  "distractor_analysis": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
  "refutational_hints": {{"B": "...", "C": "...", "D": "...", "E": "..."}},
  "comparison_table": "| Parameter | Correct Option | Main Distractor |\\n|---|---|---|\\n..."
}}
"""
    return prompt.strip()


def validate_question_flaws(question_data: Dict[str, Any], allow_negative: bool = False) -> List[str]:
    """
    Validates question against NBME item-writing standards and schema requirements.
    Returns a list of warnings / flaw messages.
    """
    flaws = []
    
    # 1. Check correct key exists
    options = question_data.get("options", {})
    correct_key = question_data.get("correct_key", "")
    if correct_key not in options:
        flaws.append(f"Correct key '{correct_key}' is not among options {list(options.keys())}")

    # 2. Lead in ends with question mark
    lead_in = question_data.get("lead_in", "").strip()
    if not lead_in.endswith("?"):
        flaws.append("Lead-in does not end with a question mark ('?')")

    # 3. Check negative stem
    if not allow_negative:
        vignette = question_data.get("vignette", "")
        combined = f"{vignette} {lead_in}"
        for bad_word in ["EXCEPT", "NOT ", "LEAST", "INCORRECT"]:
            if bad_word in combined:
                flaws.append(f"Contains negative stem '{bad_word}', which violates NBME guidelines")

    # 4. Check 'all of the above' / 'none of the above'
    for opt_key, opt_text in options.items():
        if any(forbidden in opt_text.lower() for forbidden in ["all of the above", "none of the above", "both a and b"]):
            flaws.append(f"Option {opt_key} uses '{opt_text}', which compromises discrimination power")

    # 5. Length outlier check (correct answer length vs shortest distractor)
    if correct_key in options:
        correct_len = len(options[correct_key].split())
        distractor_lens = [len(text.split()) for k, text in options.items() if k != correct_key]
        if distractor_lens:
            min_distractor = min(distractor_lens)
            if min_distractor > 0 and correct_len >= 3 * min_distractor and correct_len > 15:
                flaws.append(f"Length cue flaw: correct option ({correct_len} words) is >= 3x longer than shortest distractor ({min_distractor} words)")

    # 6. Distractor analysis completeness
    distractor_analysis = question_data.get("distractor_analysis", {})
    for opt_key in options:
        if opt_key not in distractor_analysis or not distractor_analysis[opt_key].strip():
            flaws.append(f"Missing explanation in distractor_analysis for option {opt_key}")

    return flaws


def append_to_qbank(question: QBankQuestion, qbank_path: str = "data/qbank.jsonl") -> bool:
    out_file = Path(qbank_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Check for duplicate ID
    if out_file.exists():
        with open(out_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    existing = json.loads(line)
                    if existing.get("id") == question.id:
                        console.print(f"[yellow]⚠️ Question ID '{question.id}' already exists in {qbank_path}. Skipping duplicate.[/yellow]")
                        return False
                except json.JSONDecodeError:
                    continue

    with open(out_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(question.model_dump(), ensure_ascii=False) + "\n")

    return True


from tools.llm_client import generate_structured_json


def auto_forge_questions(
    chunk_file: str,
    count: int = 5,
    profile_path: str = "data/exam_style.json",
    qbank_path: str = "data/qbank.jsonl",
    allow_flaws: bool = False,
) -> int:
    chunk_p = Path(chunk_file)
    if not chunk_p.exists():
        console.print(f"[red]Error: Chunk file '{chunk_file}' not found.[/red]")
        return 0

    with open(chunk_p, "r", encoding="utf-8") as f:
        chunks_data = [json.loads(line) for line in f if line.strip()]

    if not chunks_data:
        console.print(f"[yellow]No chunks found in '{chunk_file}'.[/yellow]")
        return 0

    style_profile = None
    prof_p = Path(profile_path)
    if prof_p.exists():
        with open(prof_p, "r", encoding="utf-8") as f:
            style_profile = ExamStyleProfile(**json.load(f))
            console.print(f"[green]✔ Active Style Profile loaded: {style_profile.style_name} (Track A)[/green]")
    else:
        console.print("[blue]ℹ No exam profile found. Using Track B (Pedagogical Mastery Mode)[/blue]")

    success_count = 0
    total_to_forge = min(count, len(chunks_data))

    for idx in range(total_to_forge):
        chunk = ContentChunk(**chunks_data[idx])
        console.print(f"\n[bold cyan]Forging question {idx + 1}/{total_to_forge}...[/bold cyan] ([dim]{chunk.chunk_id}[/dim])")

        prompt = build_forge_prompt(chunk, style_profile)
        system_prompt = "You are an elite academic and medical test constructor. Always output strictly valid JSON adhering to the provided schema with no markdown explanations outside the JSON."

        try:
            q_dict = generate_structured_json(system_prompt, prompt)
            question = QBankQuestion(**q_dict)

            flaws = validate_question_flaws(q_dict, allow_negative=(style_profile and style_profile.allows_negative_stems))
            if flaws:
                console.print("[yellow]⚠️ Flaws detected:[/yellow] " + ", ".join(flaws))
                if not allow_flaws:
                    console.print("[red]Skipping question due to item flaws.[/red]")
                    continue

            if append_to_qbank(question, qbank_path):
                console.print(f"[green]✅ Forged and saved: {question.id} ('{question.lead_in[:50]}...')[/green]")
                success_count += 1

        except Exception as e:
            console.print(f"[red]❌ Forging failed for chunk {chunk.chunk_id}: {e}[/red]")

    return success_count


def main():
    parser = argparse.ArgumentParser(description="Forge, validate, and manage PDF-School question banks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Auto-forge subcommand
    p_auto = subparsers.add_parser("auto-forge", help="Automatically generate questions using the active LLM backend")
    p_auto.add_argument("--chunk-file", required=True, help="Path to chunk JSONL file")
    p_auto.add_argument("--count", type=int, default=5, help="Number of questions to forge")
    p_auto.add_argument("--profile", default="data/exam_style.json", help="Path to exam style profile")
    p_auto.add_argument("--qbank", default="data/qbank.jsonl", help="Target qbank.jsonl path")
    p_auto.add_argument("--allow-flaws", action="store_true", help="Allow ingestion despite NBME item flaws")

    # Prompt builder subcommand
    p_prompt = subparsers.add_parser("build-prompt", help="Generate forging prompt for a chunk")
    p_prompt.add_argument("--chunk-file", required=True, help="Path to chunk JSONL file")
    p_prompt.add_argument("--chunk-index", type=int, default=0, help="Index of chunk to prompt")
    p_prompt.add_argument("--profile", default="data/exam_style.json", help="Path to exam style profile")

    # Ingestion subcommand
    p_ingest = subparsers.add_parser("ingest", help="Validate and ingest a forged question JSON into qbank.jsonl")
    p_ingest.add_argument("question_json", help="Path to question JSON file or raw JSON string")
    p_ingest.add_argument("--qbank", default="data/qbank.jsonl", help="Target qbank.jsonl path")
    p_ingest.add_argument("--allow-flaws", action="store_true", help="Allow ingestion despite NBME item flaws")

    args = parser.parse_args()

    if args.command == "auto-forge":
        count = auto_forge_questions(
            chunk_file=args.chunk_file,
            count=args.count,
            profile_path=args.profile,
            qbank_path=args.qbank,
            allow_flaws=args.allow_flaws,
        )
        console.print(f"\n[bold green]🎉 Auto-forge completed: {count} questions added to {args.qbank}[/bold green]")

    elif args.command == "build-prompt":
        chunk_path = Path(args.chunk_file)
        if not chunk_path.exists():
            console.print(f"[red]Error: Chunk file '{args.chunk_file}' not found.[/red]")
            sys.exit(1)
        
        with open(chunk_path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
        
        if args.chunk_index >= len(lines):
            console.print(f"[red]Error: Chunk index {args.chunk_index} out of range ({len(lines)} chunks available).[/red]")
            sys.exit(1)

        chunk_data = json.loads(lines[args.chunk_index])
        chunk = ContentChunk(**chunk_data)

        style_profile = None
        prof_path = Path(args.profile)
        if prof_path.exists():
            with open(prof_path, "r", encoding="utf-8") as f:
                style_profile = ExamStyleProfile(**json.load(f))
                console.print(f"[green]✔ Active Style Profile loaded: {style_profile.style_name} (Track A)[/green]")
        else:
            console.print("[blue]ℹ No profile found. Using Track B (Pedagogical Mastery Mode)[/blue]")

        prompt = build_forge_prompt(chunk, style_profile)
        print("\n" + "=" * 40 + " GENERATION PROMPT " + "=" * 40)
        print(prompt)
        print("=" * 99 + "\n")

    elif args.command == "ingest":
        q_raw = args.question_json
        if Path(q_raw).exists():
            with open(q_raw, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(q_raw)

        # Validate against schema
        try:
            question = QBankQuestion(**data)
        except Exception as e:
            console.print(f"[red]Schema Validation Error:[/red] {e}")
            sys.exit(1)

        # Check NBME flaws
        flaws = validate_question_flaws(data)
        if flaws:
            console.print("[yellow]⚠️ NBME Item-Writing Warnings Detected:[/yellow]")
            for fl in flaws:
                console.print(f"  - {fl}")
            if not args.allow_flaws:
                console.print("[red]❌ Ingestion aborted due to item-writing flaws. Use --allow-flaws to override.[/red]")
                sys.exit(1)

        success = append_to_qbank(question, args.qbank)
        if success:
            console.print(f"[green]✅ Successfully validated and appended question '{question.id}' to {args.qbank}[/green]")


if __name__ == "__main__":
    main()

