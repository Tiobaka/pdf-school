#!/usr/bin/env python3
"""
scheduler.py - FSRS-5 (Free Spaced Repetition Scheduler) for PDF-School.
Processes user study telemetry from history.jsonl and calculates daily review queues.
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
from datetime import datetime, timezone
from typing import Dict, List, Set

from fsrs import Card, Rating, Scheduler, State
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(PROJECT_ROOT))
from tools.schemas import DailySchedule, HistoryRecord, QBankQuestion

DEFAULT_QBANK = str(PROJECT_ROOT / "data" / "qbank.jsonl")
DEFAULT_HISTORY = str(PROJECT_ROOT / "data" / "history.jsonl")
DEFAULT_SCHEDULE = str(PROJECT_ROOT / "data" / "schedule.json")



console = Console()


def compute_question_fsrs_states(
    history_path: str = "data/history.jsonl",
) -> Dict[str, Card]:
    """
    Replays history.jsonl to compute the current FSRS Card state for each question.
    """
    path = Path(history_path)
    if not path.exists():
        return {}

    scheduler = Scheduler()
    cards: Dict[str, Card] = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec_data = json.loads(line)
                rec = HistoryRecord(**rec_data)
            except Exception:
                continue

            q_id = rec.question_id
            if q_id not in cards:
                cards[q_id] = Card()

            # Map user outcome & confidence to FSRS Rating
            if not rec.is_correct:
                rating = Rating.Again
            else:
                if rec.confidence_rating == "blind_guess":
                    rating = Rating.Hard
                elif rec.confidence_rating == "educated_guess":
                    rating = Rating.Good
                else:  # certain
                    rating = Rating.Easy

            # Parse record timestamp
            try:
                review_time = datetime.fromisoformat(rec.timestamp)
                if review_time.tzinfo is None:
                    review_time = review_time.replace(tzinfo=timezone.utc)
            except Exception:
                review_time = datetime.now(timezone.utc)

            updated_card, _ = scheduler.review_card(cards[q_id], rating, review_time)
            cards[q_id] = updated_card

    return cards


def generate_daily_schedule(
    qbank_path: str = "data/qbank.jsonl",
    history_path: str = "data/history.jsonl",
    output_path: str = "data/schedule.json",
    max_reviews: int = 30,
    max_new: int = 15,
) -> DailySchedule:
    # 1. Load all available question IDs
    all_q_ids: List[str] = []
    q_bank_file = Path(qbank_path)
    if q_bank_file.exists():
        with open(q_bank_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    all_q_ids.append(data["id"])
                except Exception:
                    continue

    # 2. Compute memory state for reviewed questions
    cards = compute_question_fsrs_states(history_path)
    now = datetime.now(timezone.utc)

    # 3. Identify due reviews
    due_reviews: List[str] = []
    seen_ids: Set[str] = set(cards.keys())

    for q_id, card in cards.items():
        card_due = card.due
        if card_due.tzinfo is None:
            card_due = card_due.replace(tzinfo=timezone.utc)
        if card_due <= now:
            due_reviews.append(q_id)

    # 4. Identify unencountered (new) questions
    unseen_ids = [qid for qid in all_q_ids if qid not in seen_ids]

    selected_reviews = due_reviews[:max_reviews]
    selected_new = unseen_ids[:max_new]

    today_str = now.strftime("%Y-%m-%d")
    schedule = DailySchedule(
        date=today_str,
        due_reviews=selected_reviews,
        new_questions=selected_new,
    )

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(schedule.model_dump(), f, indent=2)

    return schedule


def display_schedule(schedule: DailySchedule):
    table = Table(title=f"📅 Daily Study Block ({schedule.date})", show_header=True, header_style="bold blue")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="bold green")
    table.add_column("Description", style="dim")

    table.add_row("Due Reviews", str(len(schedule.due_reviews)), "FSRS Spaced Repetition cards ready for retrieval practice")
    table.add_row("New Questions", str(len(schedule.new_questions)), "Unencountered curriculum questions")
    table.add_row("Total Block", str(len(schedule.due_reviews) + len(schedule.new_questions)), "Target daily session load")

    console.print(Panel(table, title="[bold]PDF-School FSRS Scheduler[/bold]", border_style="cyan"))


def main():
    parser = argparse.ArgumentParser(description="FSRS Spaced Repetition study scheduler for PDF-School")
    parser.add_argument("--qbank", default="data/qbank.jsonl", help="Path to qbank.jsonl")
    parser.add_argument("--history", default="data/history.jsonl", help="Path to history.jsonl")
    parser.add_argument("--output", default="data/schedule.json", help="Path to schedule.json")
    parser.add_argument("--max-reviews", type=int, default=30, help="Maximum review questions per day")
    parser.add_argument("--max-new", type=int, default=15, help="Maximum new questions per day")

    args = parser.parse_args()
    schedule = generate_daily_schedule(
        qbank_path=args.qbank,
        history_path=args.history,
        output_path=args.output,
        max_reviews=args.max_reviews,
        max_new=args.max_new,
    )
    display_schedule(schedule)


if __name__ == "__main__":
    main()
