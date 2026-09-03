#!/usr/bin/env python3
"""
tutor_cli.py - Fast, high-yield terminal examination runner for PDF-School.
Supports Tutor Mode, Timed Block Mode, Metacognitive Calibration,
Refutational Feedback, Source Peek, and Tri-Partite Error Logging.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.schemas import HistoryRecord, QBankQuestion


console = Console()


def load_qbank(qbank_path: str = "data/qbank.jsonl") -> List[QBankQuestion]:
    path = Path(qbank_path)
    if not path.exists():
        console.print(f"[red]Error: Question bank '{qbank_path}' not found.[/red]")
        return []
    questions = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                questions.append(QBankQuestion(**data))
            except Exception as e:
                continue
    return questions


def log_history(record: HistoryRecord, history_path: str = "data/history.jsonl"):
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")


def display_source_peek(source_ref: Dict[str, str]):
    chunk_id = source_ref.get("chunk_id", "Unknown")
    source_file = source_ref.get("source_file", "Unknown")
    page = source_ref.get("page", "Unknown")

    peek_text = f"**Source Document:** `{source_file}`\n**Page / Slide:** {page}\n**Chunk ID:** `{chunk_id}`\n\n"

    # Attempt to locate source chunk in content/
    found_text = None
    for jsonl_file in Path("content").glob("*_chunks.jsonl"):
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("chunk_id") == chunk_id:
                        found_text = data.get("text")
                        break
            if found_text:
                break
        except Exception:
            continue

    if found_text:
        peek_text += f"**Source Chunk Content:**\n```\n{found_text[:800]}...\n```"
    else:
        peek_text += "*(Source chunk text file not found in local content/ directory)*"

    console.print(Panel(Markdown(peek_text), title="[cyan]📖 Source Material Peek[/cyan]", border_style="cyan"))


def run_question_session(
    q: QBankQuestion,
    q_index: int,
    total_q: int,
    tutor_mode: bool = True,
    history_path: str = "data/history.jsonl",
) -> HistoryRecord:
    console.clear()
    
    # Header
    hammer_display = "🔨" * q.difficulty_hammer
    console.print(f"[bold cyan]Question {q_index}/{total_q}[/bold cyan] | [magenta]{q.topic} - {q.subtopic or 'General'}[/magenta] | [yellow]{hammer_display}[/yellow] | [dim]{q.cognitive_level}[/dim]\n")

    # Vignette
    console.print(Panel(q.vignette, title="[bold]Clinical / Practical Scenario[/bold]", border_style="blue"))
    console.print(f"\n[bold]{q.lead_in}[/bold]\n")

    # Interactive choice tracking
    eliminated: Set[str] = set()
    start_time = time.time()
    selected_key = None
    original_selection = None
    switched = False

    while True:
        # Display options
        for key in sorted(q.options.keys()):
            opt_text = q.options[key]
            if key in eliminated:
                console.print(f"  [dim red strike]{key}) {opt_text} (Eliminated)[/dim red strike]")
            else:
                console.print(f"  [bold white]{key})[/bold white] {opt_text}")

        console.print("\n[dim]Commands: [A-E] to select | [x A] to eliminate/strike | [v] view source | [q] quit[/dim]")
        user_input = Prompt.ask("Your Choice").strip()

        if not user_input:
            continue

        if user_input.lower() == "q":
            console.print("[yellow]Session terminated by user.[/yellow]")
            sys.exit(0)

        if user_input.lower() == "v":
            display_source_peek(q.source_ref)
            continue

        if user_input.lower().startswith("x "):
            strike_target = user_input[2:].strip().upper()
            if strike_target in q.options:
                if strike_target in eliminated:
                    eliminated.remove(strike_target)
                else:
                    eliminated.add(strike_target)
            continue

        choice = user_input.upper()
        if choice in q.options:
            if selected_key is not None and choice != selected_key:
                switched = True
                original_selection = selected_key
            selected_key = choice
            break
        else:
            console.print("[red]Invalid selection. Please choose an available option.[/red]")

    elapsed_time = round(time.time() - start_time, 1)

    # Metacognitive Calibration Check
    console.print("\n[bold cyan]Metacognitive Calibration:[/bold cyan]")
    console.print("  [1] Certain (High confidence)")
    console.print("  [2] Educated Guess (Moderate confidence)")
    console.print("  [3] Blind Guess (Low confidence)")
    conf_choice = Prompt.ask("Confidence Level", choices=["1", "2", "3"], default="2")
    conf_map = {"1": "certain", "2": "educated_guess", "3": "blind_guess"}
    confidence_rating = conf_map[conf_choice]

    is_correct = (selected_key == q.correct_key)
    error_cat = None
    user_note = None

    # Tutor Mode Immediate Breakdown
    if tutor_mode:
        console.print("\n" + "=" * 80)
        if is_correct:
            console.print(f"[bold green]✔ CORRECT! Single best answer is ({q.correct_key})[/bold green]")
        else:
            console.print(f"[bold red]✘ INCORRECT. You selected ({selected_key}), but the correct answer is ({q.correct_key})[/bold red]")
            
            # Refutational Feedback for chosen distractor
            if selected_key in q.refutational_hints and q.refutational_hints[selected_key]:
                console.print(Panel(
                    q.refutational_hints[selected_key],
                    title=f"[bold yellow]⚠️ Refutation of Option ({selected_key})[/bold yellow]",
                    border_style="yellow"
                ))

            # Diagnostic Error Categorization
            console.print("\n[bold magenta]Error Analysis (Tri-Partite Taxonomy):[/bold magenta]")
            console.print("  [1] Knowledge Gap (Did not know the required fact or mechanism)")
            console.print("  [2] Misconception (Understood premise but flawed logic or confused concepts)")
            console.print("  [3] Process / Execution Error (Misread the stem, rushed, or second-guessed)")
            err_choice = Prompt.ask("Categorize your mistake", choices=["1", "2", "3"], default="1")
            err_map = {"1": "knowledge_gap", "2": "misconception", "3": "execution_error"}
            error_cat = err_map[err_choice]

        # Detailed Distractor Analysis
        console.print("\n[bold underline]Option Analysis:[/bold underline]")
        for k in sorted(q.options.keys()):
            analysis = q.distractor_analysis.get(k, "No explanation provided.")
            if k == q.correct_key:
                console.print(f"[green]({k}) {analysis}[/green]")
            else:
                console.print(f"[dim white]({k}) {analysis}[/dim white]")

        # Contrasting Cases Matrix if available
        if q.comparison_table:
            console.print(Panel(Markdown(q.comparison_table), title="[bold cyan]⚖️ Differential Comparison Matrix[/bold cyan]", border_style="cyan"))

        # Takeaway Anchor / Educational Objective
        console.print(Panel(
            f"[bold]{q.educational_objective}[/bold]",
            title="[bold green]🎯 Educational Objective (Takeaway Anchor)[/bold green]",
            border_style="green"
        ))

        Prompt.ask("\n[bold cyan]Press Enter to proceed to next question...[/bold cyan]")

    record = HistoryRecord(
        question_id=q.id,
        selected_key=selected_key,
        correct_key=q.correct_key,
        is_correct=is_correct,
        time_spent_seconds=elapsed_time,
        confidence_rating=confidence_rating,
        switched_answer=switched,
        original_selection=original_selection,
        error_category=error_cat,
        user_note=user_note,
    )
    log_history(record, history_path)
    return record


def main():
    parser = argparse.ArgumentParser(description="PDF-School Terminal Examination Runner")
    parser.add_argument("--qbank", default="data/qbank.jsonl", help="Question bank JSONL file")
    parser.add_argument("--history", default="data/history.jsonl", help="History telemetry file")
    parser.add_argument("--topic", help="Filter by topic")
    parser.add_argument("--count", type=int, default=10, help="Maximum number of questions to test")
    parser.add_argument("--mode", choices=["tutor", "timed"], default="tutor", help="Examination mode")
    parser.add_argument("--tui", action="store_true", help="Launch in visual split-screen Textual TUI")

    args = parser.parse_args()
    questions = load_qbank(args.qbank)
    if not questions:
        console.print("[yellow]No questions available to start session.[/yellow]")
        sys.exit(0)

    if args.topic:
        questions = [q for q in questions if args.topic.lower() in q.topic.lower()]

    session_questions = questions[:args.count]

    if args.tui:
        from tools.tutor_tui import TutorTUIApp
        app = TutorTUIApp(questions=session_questions, mode=args.mode, history_path=args.history)
        app.run()
        return

    tutor_mode = (args.mode == "tutor")

    console.print(f"[bold green]Starting {args.mode.upper()} session with {len(session_questions)} questions...[/bold green]")
    time.sleep(1)


    correct_count = 0
    records = []
    for idx, q in enumerate(session_questions, 1):
        rec = run_question_session(q, idx, len(session_questions), tutor_mode=tutor_mode, history_path=args.history)
        records.append(rec)
        if rec.is_correct:
            correct_count += 1

    # End of Session Summary
    console.clear()
    score_pct = round((correct_count / len(session_questions)) * 100, 1)
    summary_table = Table(title="📊 Session Performance Report", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold green" if score_pct >= 70 else "bold red")
    summary_table.add_row("Total Questions", str(len(session_questions)))
    summary_table.add_row("Score", f"{correct_count}/{len(session_questions)} ({score_pct}%)")
    
    avg_time = round(sum(r.time_spent_seconds for r in records) / len(records), 1) if records else 0
    summary_table.add_row("Avg Time Per Question", f"{avg_time}s")
    
    switched_count = sum(1 for r in records if r.switched_answer)
    summary_table.add_row("Switched Answers", str(switched_count))

    console.print(Panel(summary_table, border_style="blue"))


if __name__ == "__main__":
    main()
