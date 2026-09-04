#!/usr/bin/env python3
"""
roadmap.py - Deterministic study roadmap engine and dynamic rebalancer for PDF-School.
Calculates daily progress, detects study deficits (backlog), and deterministically
redistributes uncompleted study goals across remaining active days without requiring an LLM.
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
from datetime import date, datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

DEFAULT_ROADMAP_PATH = PROJECT_ROOT / "data" / "roadmap.json"
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "data" / "history.jsonl"

console = Console()


def load_roadmap(roadmap_path: Path = DEFAULT_ROADMAP_PATH) -> dict[str, Any]:
    if not roadmap_path.exists():
        raise FileNotFoundError(f"Roadmap file '{roadmap_path}' not found.")
    with open(roadmap_path, encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, dict) else {}


def save_roadmap(data: dict[str, Any], roadmap_path: Path = DEFAULT_ROADMAP_PATH):
    roadmap_path.parent.mkdir(parents=True, exist_ok=True)
    with open(roadmap_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_actual_vignettes_completed_by_date(
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> dict[str, int]:
    """
    Parses history.jsonl and counts unique questions attempted or total questions answered per calendar date.
    Returns: { 'YYYY-MM-DD': count }
    """
    if not history_path.exists():
        return {}

    counts: dict[str, int] = {}
    with open(history_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ts_str = rec.get("timestamp", "")
                if ts_str:
                    # ISO 8601 string -> YYYY-MM-DD
                    dt = datetime.fromisoformat(ts_str)
                    day_key = dt.strftime("%Y-%m-%d")
                    counts[day_key] = counts.get(day_key, 0) + 1
            except Exception:
                continue
    return counts


def get_day_info(roadmap: dict[str, Any], target_date: str) -> dict[str, Any] | None:
    for d in roadmap.get("days", []):
        if isinstance(d, dict) and d.get("date") == target_date:
            return d
    return None


def calculate_progress_and_debt(
    roadmap: dict[str, Any],
    as_of_date: str,
    history_counts: dict[str, int] | None = None,
) -> tuple[int, int, int, list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Analyzes all days up to as_of_date.
    Returns:
      (total_planned_past, total_completed_past, net_debt, past_days, future_active_days)
    """
    if history_counts is None:
        history_counts = get_actual_vignettes_completed_by_date()

    total_planned_past = 0
    total_completed_past = 0
    past_days = []
    future_active_days = []

    for d in roadmap.get("days", []):
        day_str = d.get("date")
        target_v = d.get("target_vignettes", 0)
        actual_v = history_counts.get(day_str, d.get("completed_vignettes", 0))

        if day_str < as_of_date:
            total_planned_past += target_v
            total_completed_past += actual_v
            past_days.append({**d, "actual_vignettes": actual_v})
        elif day_str == as_of_date:
            past_days.append({**d, "actual_vignettes": actual_v})
        else:
            if not d.get("is_rest") and d.get("target_vignettes", 0) > 0:
                future_active_days.append(d)

    debt = max(0, total_planned_past - total_completed_past)
    return total_planned_past, total_completed_past, debt, past_days, future_active_days


def rebalance_schedule(
    roadmap: dict[str, Any],
    as_of_date: str,
    history_counts: dict[str, int] | None = None,
    spread_across_days: int = 5,
) -> tuple[dict[str, Any], int, list[tuple[str, int, int]]]:
    """
    Deterministic reallocation:
    1. Calculates debt from past days (< as_of_date).
    2. Identifies upcoming active days (excluding rest days and milestone exam days).
    3. Evenly distributes the debt over the next `spread_across_days` active study days.
    4. Returns updated roadmap, total debt redistributed, and list of changes [(date, old_target, new_target)].
    """
    if history_counts is None:
        history_counts = get_actual_vignettes_completed_by_date()

    _, _, debt, _, future_days = calculate_progress_and_debt(roadmap, as_of_date, history_counts)

    if debt == 0 or not future_days:
        return roadmap, 0, []

    # Filter out milestone exam days if they have special high load (>40)
    rebalance_pool = [d for d in future_days if d.get("target_vignettes", 0) <= 25][
        :spread_across_days
    ]
    if not rebalance_pool:
        rebalance_pool = future_days[:spread_across_days]

    num_days = len(rebalance_pool)
    base_add = debt // num_days
    remainder = debt % num_days

    changes = []
    # Build lookup by date in roadmap
    days_dict = {d["date"]: d for d in roadmap["days"]}

    for i, target_day in enumerate(rebalance_pool):
        day_date = target_day["date"]
        old_val = days_dict[day_date]["target_vignettes"]
        extra = base_add + (1 if i < remainder else 0)
        new_val = old_val + extra
        days_dict[day_date]["target_vignettes"] = new_val
        changes.append((day_date, old_val, new_val))

    return roadmap, debt, changes


def print_today_view(as_of_date: str, roadmap: dict[str, Any] | None = None):
    if roadmap is None:
        roadmap = load_roadmap()

    history_counts = get_actual_vignettes_completed_by_date()
    day_info = get_day_info(roadmap, as_of_date)

    if not day_info:
        console.print(f"[yellow]No scheduled session found for date {as_of_date}.[/yellow]")
        return

    is_rest = day_info.get("is_rest", False)
    phase = day_info.get("phase", 1)
    day_num = day_info.get("day_num")
    module = day_info.get("module", "General")
    topic = day_info.get("topic", "")
    target_v = day_info.get("target_vignettes", 0)
    actual_v = history_counts.get(as_of_date, 0)
    checkpoint = day_info.get("milestone_checkpoint", "None")

    title_str = f"📚 Study Roadmap: {as_of_date}"
    if day_num:
        title_str += f" | Phase {phase} (Day {day_num} of 35)"
    else:
        title_str += " | Scheduled Rest"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Val")

    table.add_row("Module", f"[magenta]{module}[/magenta]")
    table.add_row("Topic", f"[bold white]{topic}[/bold white]")

    if is_rest:
        table.add_row("Status", "[bold green]😴 REST DAY — Full neurological recovery[/bold green]")
    else:
        progress_pct = int(actual_v / target_v * 100) if target_v > 0 else 100
        color = "green" if actual_v >= target_v else ("yellow" if actual_v > 0 else "red")
        table.add_row(
            "Vignettes", f"[{color}]{actual_v} / {target_v} completed ({progress_pct}%)[/{color}]"
        )

    table.add_row("Checkpoint", f"[dim]{checkpoint}[/dim]")

    tasks = day_info.get("tasks", [])
    if tasks:
        tasks_formatted = "\n".join([f"  • {t}" for t in tasks])
        table.add_row("Tasks", tasks_formatted)

    # Next milestone countdown
    for ms in roadmap.get("milestones", []):
        if ms["date"] >= as_of_date:
            ms_date = date.fromisoformat(ms["date"])
            cur_date = date.fromisoformat(as_of_date)
            delta_days = (ms_date - cur_date).days
            table.add_row(
                "Upcoming Target",
                f"[bold yellow]{ms['name']}[/bold yellow] in [bold]{delta_days} days[/bold] ({ms['date']})",
            )
            break

    console.print(Panel(table, title=f"[bold blue]{title_str}[/bold blue]", border_style="blue"))


def print_status_view(as_of_date: str, roadmap: dict[str, Any] | None = None):
    if roadmap is None:
        roadmap = load_roadmap()

    history_counts = get_actual_vignettes_completed_by_date()
    planned_past, completed_past, debt, past_days, future_days = calculate_progress_and_debt(
        roadmap, as_of_date, history_counts
    )

    table = Table(
        title=f"📊 Roadmap Global Status (as of {as_of_date})",
        show_header=True,
        header_style="bold green",
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="bold")
    table.add_column("Notes", style="dim")

    table.add_row(
        "Exam Target", roadmap.get("exam_target", "Final"), f"Exam Date: {roadmap.get('exam_date')}"
    )
    table.add_row(
        "Active Study Days Elapsed",
        str(len([d for d in past_days if not d.get("is_rest")])),
        "out of 35 active days",
    )
    table.add_row("Remaining Active Days", str(len(future_days)), "excluding rest days")
    table.add_row("Cumulative Planned Vignettes", str(planned_past), "target up to today")
    table.add_row(
        "Cumulative Completed Vignettes", str(completed_past), "verified via history.jsonl"
    )

    debt_style = "bold green" if debt == 0 else "bold red"
    debt_msg = "On track!" if debt == 0 else f"Deficit: {debt} questions behind schedule"
    table.add_row("Current Backlog / Debt", f"[{debt_style}]{debt}[/{debt_style}]", debt_msg)

    console.print(table)

    if debt > 0:
        console.print(
            f"[yellow]💡 Tip: Run `tools/roadmap.py rebalance` to deterministically redistribute {debt} backlog questions over upcoming active days.[/yellow]\n"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic Study Roadmap and Rebalancer for PDF-School"
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # today
    today_parser = subparsers.add_parser("today", help="Show today's module and tasks")
    today_parser.add_argument(
        "--date", default=date.today().isoformat(), help="Target date (YYYY-MM-DD)"
    )

    # status
    status_parser = subparsers.add_parser(
        "status", help="Show overall study pace, debt, and countdown"
    )
    status_parser.add_argument(
        "--date", default=date.today().isoformat(), help="Target date (YYYY-MM-DD)"
    )

    # rebalance
    rebalance_parser = subparsers.add_parser(
        "rebalance", help="Deterministically redistribute uncompleted debt"
    )
    rebalance_parser.add_argument(
        "--date", default=date.today().isoformat(), help="Current date (YYYY-MM-DD)"
    )
    rebalance_parser.add_argument(
        "--spread", type=int, default=5, help="Number of active days to spread debt over"
    )

    args = parser.parse_args()
    cmd = args.command or "today"

    if cmd == "today":
        print_today_view(args.date)
    elif cmd == "status":
        print_status_view(args.date)
    elif cmd == "rebalance":
        roadmap = load_roadmap()
        history_counts = get_actual_vignettes_completed_by_date()
        updated_roadmap, debt, changes = rebalance_schedule(
            roadmap, args.date, history_counts, spread_across_days=args.spread
        )
        if debt == 0:
            console.print("[green]✔ No debt detected. You are completely on schedule![/green]")
        else:
            save_roadmap(updated_roadmap)
            console.print(
                f"[bold green]✔ Successfully redistributed {debt} backlog questions across {len(changes)} active study days:[/bold green]"
            )
            tbl = Table(show_header=True, header_style="bold magenta")
            tbl.add_column("Date", style="cyan")
            tbl.add_column("Previous Target", justify="right")
            tbl.add_column("New Daily Target", justify="right", style="bold green")
            tbl.add_column("Delta", justify="right", style="yellow")
            for d_str, old_v, new_v in changes:
                tbl.add_row(d_str, str(old_v), str(new_v), f"+{new_v - old_v}")
            console.print(tbl)
            console.print(f"💾 Updated: [dim]{DEFAULT_ROADMAP_PATH}[/dim]\n")


if __name__ == "__main__":
    main()
