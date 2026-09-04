import click
from rich.console import Console
from rich.table import Table

from pdf_school import __version__
from pdf_school.core.config import PROJECT_ROOT, get_content_dir, get_data_dir, get_sources_dir

console = Console()


@click.group()
@click.version_option(__version__, prog_name="pdf-school")
def cli():
    """📚 PDF-School: The UNIX-style agentic study engine."""
    pass


# 1. Ingest
@cli.command("ingest")
@click.argument("target", type=click.Path(exists=True))
@click.option("--chunk-size", default=500, help="Target word count per chunk")
def ingest(target: str, chunk_size: int):
    """Ingest documents (.pdf, .docx, .pptx) into normalized text chunks."""
    from pdf_school.core.extract import process_file_or_dir

    process_file_or_dir(
        target,
        output_dir_str=str(get_content_dir()),
        figures_dir_str=str(get_content_dir() / "figures"),
        chunk_size=chunk_size,
    )


# 2. Profile
@cli.command("profile")
@click.option("--input", "input_dir", default=None, help="Directory containing past exams")
@click.option("--output", default=None, help="Path for generated exam_style.json")
def profile(input_dir: str | None, output: str | None):
    """Analyze past exams to synthesize a Track A Professor Style Profile."""
    from pdf_school.engine.profile_exam import display_profile, profile_exams

    inp = input_dir or str(get_sources_dir() / "past_exams")
    out = output or str(get_data_dir() / "exam_style.json")
    prof = profile_exams(inp, out)
    if prof:
        display_profile(prof, out)


# 3. Forge
@cli.command("forge")
@click.option(
    "--chunk-file",
    required=True,
    type=click.Path(exists=True),
    help="Chunk JSONL file to generate from",
)
@click.option("--count", default=5, type=int, help="Number of questions to forge")
@click.option("--profile", "profile_path", default=None, help="Path to exam_style.json")
@click.option("--qbank", default=None, help="Destination qbank.jsonl path")
def forge(chunk_file: str, count: int, profile_path: str | None, qbank: str | None):
    """Auto-forge high-yield questions from an extracted chunk file."""
    from pdf_school.engine.qbank_forge import auto_forge_questions

    prof = profile_path or str(get_data_dir() / "exam_style.json")
    qb = qbank or str(get_data_dir() / "qbank.jsonl")
    auto_forge_questions(chunk_file, count=count, profile_path=prof, qbank_path=qb)


# 4. Tutor / Exam
@cli.command("tutor")
@click.option("--mode", type=click.Choice(["tutor", "timed"]), default="tutor", help="Session mode")
@click.option("--count", default=15, type=int, help="Number of questions")
@click.option("--topic", default=None, help="Filter by topic")
@click.option("--adaptive", is_flag=True, help="Prioritize historic weakness areas")
@click.option("--cli-mode", is_flag=True, help="Use simple CLI instead of visual TUI")
def tutor(mode: str, count: int, topic: str | None, adaptive: bool, cli_mode: bool):
    """Launch interactive examination session (Visual TUI by default)."""
    qbank_path = str(get_data_dir() / "qbank.jsonl")
    history_path = str(get_data_dir() / "history.jsonl")

    if cli_mode:
        from pdf_school.tui.cli_runner import load_qbank, run_question_session

        questions = load_qbank(qbank_path)
        if topic:
            questions = [q for q in questions if topic.lower() in q.topic.lower()]
        questions = questions[:count]
        if not questions:
            console.print("[red]No questions available for session.[/red]")
            return
        for i, q in enumerate(questions, 1):
            run_question_session(
                q, i, len(questions), tutor_mode=(mode == "tutor"), history_path=history_path
            )
    else:
        from pdf_school.tui.app import TutorTUIApp, load_qbank

        questions = load_qbank(qbank_path)
        if topic:
            questions = [q for q in questions if topic.lower() in q.topic.lower()]
        questions = questions[:count]
        if not questions:
            console.print(
                "[red]No questions available in QBank. Run `pdf-school forge` first.[/red]"
            )
            return
        app = TutorTUIApp(questions=questions, mode=mode, history_path=history_path)
        app.run()


# 5. Scheduler
@cli.command("schedule")
@click.option("--date", default=None, help="Target date (YYYY-MM-DD)")
@click.option("--max-reviews", default=30, type=int)
@click.option("--max-new", default=15, type=int)
def schedule(date: str | None, max_reviews: int, max_new: int):
    """Compute today's FSRS spaced repetition review deck and study load."""
    from pdf_school.engine.scheduler import display_schedule, generate_daily_schedule

    qbank_p = str(get_data_dir() / "qbank.jsonl")
    history_p = str(get_data_dir() / "history.jsonl")
    sched_p = str(get_data_dir() / "schedule.json")
    sch = generate_daily_schedule(
        qbank_path=qbank_p,
        history_path=history_p,
        output_path=sched_p,
        max_reviews=max_reviews,
        max_new=max_new,
        target_date=date,
    )
    display_schedule(sch)

    # If roadmap exists, also display today's roadmap
    roadmap_file = get_data_dir() / "roadmap.json"
    if roadmap_file.exists():
        from datetime import datetime, timezone

        from pdf_school.engine.roadmap import print_today_view

        target_d = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print_today_view(target_d)


# 6. Roadmap
@cli.group("roadmap")
def roadmap_grp():
    """Curricular Roadmap & Deterministic Dynamic Rebalancer."""
    pass


@roadmap_grp.command("today")
@click.option("--date", default=None, help="Target date (YYYY-MM-DD)")
def roadmap_today(date: str | None):
    """Display today's module, checkpoint, and tasks."""
    from datetime import date as dt_date

    from pdf_school.engine.roadmap import print_today_view

    target_d = date or dt_date.today().isoformat()
    print_today_view(target_d)


@roadmap_grp.command("status")
@click.option("--date", default=None, help="Target date (YYYY-MM-DD)")
def roadmap_status(date: str | None):
    """Show global study pacing, deficit, and upcoming milestones."""
    from datetime import date as dt_date

    from pdf_school.engine.roadmap import print_status_view

    target_d = date or dt_date.today().isoformat()
    print_status_view(target_d)


@roadmap_grp.command("rebalance")
@click.option("--date", default=None, help="Target date (YYYY-MM-DD)")
@click.option("--spread", default=5, type=int, help="Active study days to spread backlog over")
def roadmap_rebalance(date: str | None, spread: int):
    """Deterministically redistribute missed study load over upcoming active days."""
    from datetime import date as dt_date

    from pdf_school.engine.roadmap import (
        get_actual_vignettes_completed_by_date,
        load_roadmap,
        rebalance_schedule,
        save_roadmap,
    )

    target_d = date or dt_date.today().isoformat()
    rm = load_roadmap()
    history_counts = get_actual_vignettes_completed_by_date()
    updated_rm, debt, changes = rebalance_schedule(
        rm, target_d, history_counts, spread_across_days=spread
    )
    if debt == 0:
        console.print("[green]✔ No study deficit detected. You are completely on track![/green]")
    else:
        save_roadmap(updated_rm)
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


# 7. Sync
@cli.group("sync")
def sync_grp():
    """Sync study progress with SQLite database and Anki."""
    pass


@sync_grp.command("db")
@click.option("--force", is_flag=True, help="Force full rebuild of SQLite database")
def sync_db_cmd(force: bool):
    """Sync QBank and history logs into SQLite study.db."""
    from pdf_school.bridges.study_db import sync_db

    sync_db(force=force)


@sync_grp.command("anki")
@click.option("--qbank", default="data/qbank.jsonl", help="Path to qbank.jsonl")
@click.option("--deck", default="PDF-School", help="Target deck name in Anki")
def sync_anki(qbank: str, deck: str):
    """Sync flashcard queue directly with AnkiConnect."""
    from pdf_school.bridges.anki_bridge import load_questions, sync_to_ankiconnect

    questions = load_questions(qbank)
    if not questions:
        console.print(f"[yellow]No questions found in '{qbank}'.[/yellow]")
        return
    try:
        added = sync_to_ankiconnect(questions, deck_name=deck)
        console.print(f"[green]✅ Synced {added} notes to Anki deck '[bold]{deck}[/bold]'[/green]")
    except Exception as e:
        console.print(f"[red]❌ Sync failed: {e}[/red]")


@sync_grp.command("tsv")
@click.option("--qbank", default="data/qbank.jsonl", help="Path to qbank.jsonl")
@click.option("--output", default="data/anki_cards.tsv", help="Destination TSV path")
def sync_tsv(qbank: str, output: str):
    """Export flashcards to TSV for manual Anki import."""
    from pdf_school.bridges.anki_bridge import export_to_tsv, load_questions

    questions = load_questions(qbank)
    if not questions:
        console.print(f"[yellow]No questions found in '{qbank}'.[/yellow]")
        return
    count = export_to_tsv(questions, output_tsv=output)
    console.print(f"[green]✅ Exported {count} cards to TSV at: [bold]{output}[/bold][/green]")


# 8. Doctor
@cli.command("doctor")
def doctor():
    """Check system health, dependencies, QBank status, and LLM backends."""
    import platform

    table = Table(
        title="🏥 PDF-School System Diagnostics", show_header=True, header_style="bold green"
    )
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    # Python & OS
    table.add_row(
        "Python Version", f"[green]✔ {platform.python_version()}[/green]", platform.platform()
    )
    table.add_row("PDF-School Version", f"[green]✔ v{__version__}[/green]", f"Root: {PROJECT_ROOT}")

    # Question Bank
    qbank_p = get_data_dir() / "qbank.jsonl"
    if qbank_p.exists():
        with open(qbank_p, encoding="utf-8") as f:
            q_count = sum(1 for line in f if line.strip())
        table.add_row("Question Bank", f"[green]✔ {q_count} questions[/green]", str(qbank_p))
    else:
        table.add_row("Question Bank", "[yellow]⚠️ Missing[/yellow]", "Run `pdf-school forge`")

    # Study History
    history_p = get_data_dir() / "history.jsonl"
    if history_p.exists():
        with open(history_p, encoding="utf-8") as f:
            h_count = sum(1 for line in f if line.strip())
        table.add_row("Study History", f"[green]✔ {h_count} logs recorded[/green]", str(history_p))
    else:
        table.add_row("Study History", "[blue]ℹ 0 logs[/blue]", "No exam sessions completed yet")

    # LLM Config
    from pdf_school.core.llm_client import get_llm_config

    provider, key, model, _ = get_llm_config()
    if provider != "none":
        table.add_row("LLM Backend", f"[green]✔ {provider.upper()}[/green]", f"Model: {model}")
    else:
        table.add_row(
            "LLM Backend",
            "[yellow]⚠️ None configured[/yellow]",
            "Set GEMINI_API_KEY or OPENAI_API_KEY in .env",
        )

    # AnkiConnect
    from pdf_school.bridges.anki_bridge import check_ankiconnect_health

    anki_ok = check_ankiconnect_health()
    if anki_ok:
        table.add_row(
            "AnkiConnect", "[green]✔ Connected[/green]", "http://localhost:8765 reachable"
        )
    else:
        table.add_row(
            "AnkiConnect",
            "[dim]Offline / Unreachable[/dim]",
            "Start Anki with AnkiConnect enabled to sync",
        )

    console.print(table)


if __name__ == "__main__":
    cli()
