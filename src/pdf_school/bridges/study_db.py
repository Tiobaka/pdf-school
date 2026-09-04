#!/usr/bin/env python3
"""
study_db.py - Hybrid SQLite Analytics & Weakness Triage Engine for PDF-School.
Provides an indexed, disposable, read-optimized analytical mirror of JSONL data.
Enforces unidirectional source of truth:
  User Session -> JSONL (canonical) -> SQLite (analytical mirror)
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pdf_school.core.config import PROJECT_ROOT
from pdf_school.engine.scheduler import compute_question_fsrs_states
from pdf_school.schemas import HistoryRecord, QBankQuestion

console = Console()

DEFAULT_DB = PROJECT_ROOT / "data" / "study.db"
DEFAULT_QBANK = PROJECT_ROOT / "data" / "qbank.jsonl"
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "history.jsonl"


def get_db_connection(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        # 1. Questions table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            subtopic TEXT,
            difficulty_hammer INTEGER NOT NULL CHECK (difficulty_hammer BETWEEN 1 AND 5),
            cognitive_level TEXT NOT NULL,
            lead_in TEXT NOT NULL,
            educational_objective TEXT NOT NULL,
            correct_key TEXT NOT NULL,
            source_file TEXT,
            raw_json TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            synced_at TEXT NOT NULL
        );
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_questions_topic_subtopic ON questions (topic, subtopic);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions (difficulty_hammer);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_questions_cognitive ON questions (cognitive_level);"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_active ON questions (is_active);")

        # 2. History table (denormalized topic & subtopic for fast analytical rollups)
        # Note: Foreign key on question_id is relaxed to allow historical tracking of archived or demo items
        conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            record_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            question_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            subtopic TEXT,
            selected_key TEXT NOT NULL,
            correct_key TEXT NOT NULL,
            is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
            time_spent_seconds REAL NOT NULL,
            confidence_rating TEXT NOT NULL CHECK (confidence_rating IN ('certain', 'educated_guess', 'blind_guess')),
            switched_answer INTEGER NOT NULL DEFAULT 0 CHECK (switched_answer IN (0, 1)),
            original_selection TEXT,
            error_category TEXT CHECK (error_category IN ('knowledge_gap', 'misconception', 'execution_error') OR error_category IS NULL),
            user_note TEXT
        );
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_q_time ON history (question_id, timestamp DESC);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_topic_correct ON history (topic, is_correct);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_calib ON history (confidence_rating, is_correct);"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON history (timestamp DESC);")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_errors ON history (error_category) WHERE is_correct = 0;"
        )

        # 3. FSRS Memory Mirror table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS question_fsrs (
            question_id TEXT PRIMARY KEY,
            due TEXT NOT NULL,
            stability REAL NOT NULL,
            difficulty REAL NOT NULL,
            state INTEGER NOT NULL,
            last_review TEXT,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fsrs_due ON question_fsrs (due);")

        # 4. Sync Metadata tracking
        conn.execute("""
        CREATE TABLE IF NOT EXISTS _sync_state (
            source_file TEXT PRIMARY KEY,
            mtime_ns INTEGER NOT NULL,
            file_size INTEGER NOT NULL,
            last_synced_at TEXT NOT NULL
        );
        """)


def is_file_modified(conn: sqlite3.Connection, file_path: Path) -> bool:
    if not file_path.exists():
        return False
    stat = file_path.stat()
    row = conn.execute(
        "SELECT mtime_ns, file_size FROM _sync_state WHERE source_file = ?",
        (str(file_path),),
    ).fetchone()
    if row is None:
        return True
    return bool(row["mtime_ns"] != stat.st_mtime_ns or row["file_size"] != stat.st_size)


def record_sync_state(conn: sqlite3.Connection, file_path: Path) -> None:
    if not file_path.exists():
        return
    stat = file_path.stat()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO _sync_state (source_file, mtime_ns, file_size, last_synced_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_file) DO UPDATE SET
            mtime_ns = excluded.mtime_ns,
            file_size = excluded.file_size,
            last_synced_at = excluded.last_synced_at
        """,
        (str(file_path), stat.st_mtime_ns, stat.st_size, now_iso),
    )


def sync_db(
    db_path: Path = DEFAULT_DB,
    qbank_path: Path = DEFAULT_QBANK,
    history_path: Path = DEFAULT_HISTORY,
    force: bool = False,
) -> dict[str, int]:
    """
    Idempotent, atomic synchronization from JSONL files into the SQLite mirror.
    Returns counts of questions and history records synced.
    """
    conn = get_db_connection(db_path)
    try:
        init_db(conn)
        now_iso = datetime.now(timezone.utc).isoformat()
        counts = {"questions": 0, "history": 0, "fsrs": 0}

        qbank_needs_sync = force or is_file_modified(conn, qbank_path)
        history_needs_sync = force or is_file_modified(conn, history_path)

        if not qbank_needs_sync and not history_needs_sync:
            return counts

        with conn:
            topic_map: dict[str, tuple[str, str | None]] = {}

            # 1. Sync Questions
            if qbank_needs_sync and qbank_path.exists():
                with open(qbank_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            q_data = json.loads(line)
                            q = QBankQuestion(**q_data)
                        except Exception:
                            continue

                        topic_map[q.id] = (q.topic, q.subtopic)
                        source_file = q.source_ref.get("source_file") if q.source_ref else None

                        conn.execute(
                            """
                            INSERT INTO questions (
                                id, topic, subtopic, difficulty_hammer, cognitive_level,
                                lead_in, educational_objective, correct_key, source_file,
                                raw_json, is_active, synced_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                topic = excluded.topic,
                                subtopic = excluded.subtopic,
                                difficulty_hammer = excluded.difficulty_hammer,
                                cognitive_level = excluded.cognitive_level,
                                lead_in = excluded.lead_in,
                                educational_objective = excluded.educational_objective,
                                correct_key = excluded.correct_key,
                                source_file = excluded.source_file,
                                raw_json = excluded.raw_json,
                                is_active = 1,
                                synced_at = excluded.synced_at
                            """,
                            (
                                q.id,
                                q.topic,
                                q.subtopic,
                                q.difficulty_hammer,
                                q.cognitive_level,
                                q.lead_in,
                                q.educational_objective,
                                q.correct_key,
                                source_file,
                                json.dumps(q.model_dump(), ensure_ascii=False),
                                now_iso,
                            ),
                        )
                        counts["questions"] += 1

                # Soft-delete questions not updated in this sync run (safe against SQLITE_MAX_VARIABLE_NUMBER)
                conn.execute(
                    "UPDATE questions SET is_active = 0 WHERE synced_at != ?",
                    (now_iso,),
                )
                record_sync_state(conn, qbank_path)

            # Prepopulate topic_map if not filled during questions sync
            if not topic_map:
                for row in conn.execute("SELECT id, topic, subtopic FROM questions"):
                    topic_map[row["id"]] = (row["topic"], row["subtopic"])

            # 2. Sync History
            if history_needs_sync and history_path.exists():
                with open(history_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            h_data = json.loads(line)
                            rec = HistoryRecord(**h_data)
                        except Exception:
                            continue

                        record_id = rec.compute_record_id()
                        t_info = topic_map.get(rec.question_id, ("General", None))

                        conn.execute(
                            """
                            INSERT OR IGNORE INTO history (
                                record_id, timestamp, question_id, topic, subtopic,
                                selected_key, correct_key, is_correct, time_spent_seconds,
                                confidence_rating, switched_answer, original_selection,
                                error_category, user_note
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                record_id,
                                rec.timestamp,
                                rec.question_id,
                                t_info[0],
                                t_info[1],
                                rec.selected_key,
                                rec.correct_key,
                                1 if rec.is_correct else 0,
                                rec.time_spent_seconds,
                                rec.confidence_rating,
                                1 if rec.switched_answer else 0,
                                rec.original_selection,
                                rec.error_category,
                                rec.user_note,
                            ),
                        )
                        counts["history"] += 1

                record_sync_state(conn, history_path)

            # 3. Materialize FSRS states
            if history_path.exists():
                cards = compute_question_fsrs_states(str(history_path))
                for q_id, card in cards.items():
                    due_iso = card.due.isoformat() if card.due else now_iso
                    last_rev_iso = card.last_review.isoformat() if card.last_review else None
                    conn.execute(
                        """
                        INSERT INTO question_fsrs (
                            question_id, due, stability, difficulty, state, last_review
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(question_id) DO UPDATE SET
                            due = excluded.due,
                            stability = excluded.stability,
                            difficulty = excluded.difficulty,
                            state = excluded.state,
                            last_review = excluded.last_review
                        """,
                        (
                            q_id,
                            due_iso,
                            card.stability,
                            card.difficulty,
                            int(card.state),
                            last_rev_iso,
                        ),
                    )
                    counts["fsrs"] += 1

        return counts
    finally:
        conn.close()


def get_weakness_queue(
    db_path: Path = DEFAULT_DB,
    qbank_path: Path = DEFAULT_QBANK,
    history_path: Path = DEFAULT_HISTORY,
    limit: int = 15,
    topic: str | None = None,
) -> list[QBankQuestion]:
    """
    Generates an adaptive remediation block targeting:
      1. Entrenched misconceptions & high-confidence failures (Dunning-Kruger blunders)
      2. Recent knowledge gaps / lapses
      3. Lucky blind guesses that need reinforcement
      4. Overdue FSRS cards in weak subjects
      5. Unseen questions in struggling topics
    """
    sync_db(db_path, qbank_path, history_path)
    conn = get_db_connection(db_path)
    try:
        query = """
        WITH latest_attempt AS (
            SELECT
                question_id,
                is_correct,
                confidence_rating,
                error_category,
                timestamp,
                ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY timestamp DESC) as rn
            FROM history
        ),
        topic_stats AS (
            SELECT
                topic,
                COALESCE(AVG(is_correct), 0.5) as topic_accuracy
            FROM history
            GROUP BY topic
        )
        SELECT
            q.id,
            q.raw_json,
            (
                CASE
                    -- Tier 1: Entrenched Misconception or High-Confidence Failure
                    WHEN la.is_correct = 0 AND (la.error_category = 'misconception' OR la.confidence_rating = 'certain') THEN 1000
                    -- Tier 2: Recent Knowledge Gap or Lapsed Question
                    WHEN la.is_correct = 0 THEN 800
                    -- Tier 3: Blind Guess on Last Attempt (Lucky Guess needs reinforcement)
                    WHEN la.is_correct = 1 AND la.confidence_rating = 'blind_guess' THEN 600
                    -- Tier 4: Overdue FSRS Review in a Weak Topic (<70% accuracy)
                    WHEN f.due IS NOT NULL AND datetime(f.due) <= datetime('now') AND COALESCE(ts.topic_accuracy, 0.5) < 0.7 THEN 400
                    -- Tier 5: Unseen Question in a Weak Topic
                    WHEN la.is_correct IS NULL AND COALESCE(ts.topic_accuracy, 0.5) < 0.7 THEN 300
                    -- Tier 6: Normal Due FSRS Card
                    WHEN f.due IS NOT NULL AND datetime(f.due) <= datetime('now') THEN 200
                    -- Tier 7: Unseen Question in an Average Topic
                    WHEN la.is_correct IS NULL THEN 100
                    ELSE 10
                END
                + (1.0 - COALESCE(ts.topic_accuracy, 0.5)) * 100.0
            ) as weakness_score
        FROM questions q
        LEFT JOIN latest_attempt la ON q.id = la.question_id AND la.rn = 1
        LEFT JOIN topic_stats ts ON q.topic = ts.topic
        LEFT JOIN question_fsrs f ON q.id = f.question_id
        WHERE q.is_active = 1
          AND (:topic IS NULL OR lower(q.topic) LIKE '%' || lower(:topic) || '%')
          AND (
              la.is_correct = 0
              OR (la.is_correct = 1 AND la.confidence_rating = 'blind_guess')
              OR (f.due IS NOT NULL AND datetime(f.due) <= datetime('now'))
              OR (la.is_correct IS NULL)
          )
        ORDER BY weakness_score DESC, q.id ASC
        LIMIT :limit;
        """

        cursor = conn.execute(query, {"limit": limit, "topic": topic})
        rows = cursor.fetchall()

        questions = []
        for r in rows:
            try:
                q = QBankQuestion.model_validate_json(r["raw_json"])
                questions.append(q)
            except Exception:
                continue

        return questions
    finally:
        conn.close()


# =====================================================================
# Analytical Reporting Queries
# =====================================================================


def get_mastery_report(conn: sqlite3.Connection, topic: str | None = None) -> list[dict[str, Any]]:
    query = """
    WITH latest_attempts AS (
        SELECT
            question_id,
            topic,
            COALESCE(subtopic, 'General') as subtopic,
            is_correct,
            ROW_NUMBER() OVER (PARTITION BY question_id ORDER BY timestamp DESC) as rn
        FROM history
    ),
    topic_cumulative AS (
        SELECT
            topic,
            COALESCE(subtopic, 'General') as subtopic,
            COUNT(*) as total_attempts,
            ROUND(AVG(is_correct) * 100.0, 1) as cumulative_accuracy_pct
        FROM history
        WHERE (:topic IS NULL OR lower(topic) LIKE '%' || lower(:topic) || '%')
        GROUP BY topic, COALESCE(subtopic, 'General')
    ),
    topic_current AS (
        SELECT
            topic,
            subtopic,
            COUNT(*) as unique_seen,
            ROUND(AVG(is_correct) * 100.0, 1) as current_mastery_pct
        FROM latest_attempts
        WHERE rn = 1
          AND (:topic IS NULL OR lower(topic) LIKE '%' || lower(:topic) || '%')
        GROUP BY topic, subtopic
    )
    SELECT
        c.topic,
        c.subtopic,
        c.total_attempts,
        u.unique_seen,
        c.cumulative_accuracy_pct,
        u.current_mastery_pct
    FROM topic_cumulative c
    JOIN topic_current u ON c.topic = u.topic AND c.subtopic = u.subtopic
    ORDER BY u.current_mastery_pct ASC, c.total_attempts DESC;
    """
    cursor = conn.execute(query, {"topic": topic})
    return [dict(r) for r in cursor.fetchall()]


def get_calibration_report(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    query = """
    SELECT
        confidence_rating,
        COUNT(*) as total_attempts,
        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
        SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as incorrect_count,
        ROUND(AVG(is_correct) * 100.0, 1) as actual_accuracy_pct,
        SUM(CASE WHEN confidence_rating = 'certain' AND is_correct = 0 THEN 1 ELSE 0 END) as dunning_kruger_blunders
    FROM history
    GROUP BY confidence_rating
    ORDER BY
        CASE confidence_rating
            WHEN 'certain' THEN 1
            WHEN 'educated_guess' THEN 2
            WHEN 'blind_guess' THEN 3
        END;
    """
    cursor = conn.execute(query)
    return [dict(r) for r in cursor.fetchall()]


def get_error_taxonomy_report(
    conn: sqlite3.Connection, topic: str | None = None
) -> list[dict[str, Any]]:
    query = """
    SELECT
        topic,
        error_category,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY topic), 1) as pct_of_topic_errors,
        ROUND(AVG(time_spent_seconds), 1) as avg_seconds
    FROM history
    WHERE is_correct = 0 AND error_category IS NOT NULL
      AND (:topic IS NULL OR lower(topic) LIKE '%' || lower(:topic) || '%')
    GROUP BY topic, error_category
    ORDER BY topic, count DESC;
    """
    cursor = conn.execute(query, {"topic": topic})
    return [dict(r) for r in cursor.fetchall()]


def get_time_analysis(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    query = """
    SELECT
        switched_answer,
        COUNT(*) as count,
        ROUND(AVG(is_correct) * 100.0, 1) as accuracy_pct,
        ROUND(AVG(time_spent_seconds), 1) as avg_seconds,
        ROUND(AVG(CASE WHEN is_correct = 1 THEN time_spent_seconds END), 1) as avg_seconds_correct,
        ROUND(AVG(CASE WHEN is_correct = 0 THEN time_spent_seconds END), 1) as avg_seconds_incorrect
    FROM history
    GROUP BY switched_answer;
    """
    cursor = conn.execute(query)
    return [dict(r) for r in cursor.fetchall()]


# =====================================================================
# Terminal Display Helpers
# =====================================================================


def display_reports(
    conn: sqlite3.Connection, topic: str | None = None, report_type: str = "all"
) -> None:
    has_rendered = False

    # 1. Mastery Report
    if report_type in ["all", "mastery"]:
        mastery = get_mastery_report(conn, topic)
        if mastery:
            has_rendered = True
            t_mastery = Table(title="🎯 Subject & Subtopic Mastery", header_style="bold green")
            t_mastery.add_column("Topic", style="cyan")
            t_mastery.add_column("Subtopic", style="magenta")
            t_mastery.add_column("Attempts", justify="right")
            t_mastery.add_column("Seen", justify="right")
            t_mastery.add_column("Cumulative %", justify="right")
            t_mastery.add_column("Current Mastery %", justify="right", style="bold")

            for m in mastery:
                color = (
                    "green"
                    if m["current_mastery_pct"] >= 75
                    else ("yellow" if m["current_mastery_pct"] >= 60 else "red")
                )
                t_mastery.add_row(
                    m["topic"],
                    m["subtopic"],
                    str(m["total_attempts"]),
                    str(m["unique_seen"]),
                    f"{m['cumulative_accuracy_pct']}%",
                    f"[{color}]{m['current_mastery_pct']}%[/{color}]",
                )
            console.print(t_mastery)
            console.print()

    # 2. Metacognitive Calibration
    if report_type in ["all", "calibration"]:
        calib = get_calibration_report(conn)
        if calib:
            has_rendered = True
            t_calib = Table(
                title="⚖️ Metacognitive Calibration (Dunning-Kruger Detection)",
                header_style="bold blue",
            )
            t_calib.add_column("Confidence Level", style="cyan")
            t_calib.add_column("Attempts", justify="right")
            t_calib.add_column("Correct", justify="right", style="green")
            t_calib.add_column("Incorrect", justify="right", style="red")
            t_calib.add_column("Actual Accuracy", justify="right", style="bold")
            t_calib.add_column("High-Confidence Blunders", justify="right", style="bold red")

            for c in calib:
                t_calib.add_row(
                    c["confidence_rating"].replace("_", " ").title(),
                    str(c["total_attempts"]),
                    str(c["correct_count"]),
                    str(c["incorrect_count"]),
                    f"{c['actual_accuracy_pct']}%",
                    str(c["dunning_kruger_blunders"]),
                )
            console.print(t_calib)
            console.print()

    # 3. Tri-Partite Error Breakdown
    if report_type in ["all", "errors"]:
        errors = get_error_taxonomy_report(conn, topic)
        if errors:
            has_rendered = True
            t_errors = Table(
                title="🔍 Tri-Partite Error Taxonomy Breakdown", header_style="bold yellow"
            )
            t_errors.add_column("Topic", style="cyan")
            t_errors.add_column("Error Category", style="magenta")
            t_errors.add_column("Error Count", justify="right")
            t_errors.add_column("% of Topic Errors", justify="right")
            t_errors.add_column("Avg Time (s)", justify="right")

            for e in errors:
                cat_name = e["error_category"].replace("_", " ").title()
                t_errors.add_row(
                    e["topic"],
                    cat_name,
                    str(e["count"]),
                    f"{e['pct_of_topic_errors']}%",
                    f"{e['avg_seconds']}s",
                )
            console.print(t_errors)
            console.print()

    # 4. Time Profiling
    if report_type in ["all", "time"]:
        time_stats = get_time_analysis(conn)
        if time_stats:
            has_rendered = True
            t_time = Table(
                title="⏱️ Time Profiling & Answer Switching Payoff", header_style="bold magenta"
            )
            t_time.add_column("Switched Answer?", style="cyan")
            t_time.add_column("Count", justify="right")
            t_time.add_column("Accuracy %", justify="right", style="bold")
            t_time.add_column("Avg Total (s)", justify="right")
            t_time.add_column("Avg Correct (s)", justify="right", style="green")
            t_time.add_column("Avg Incorrect (s)", justify="right", style="red")

            for ts in time_stats:
                t_time.add_row(
                    "Yes (Second-guessed)"
                    if ts["switched_answer"] == 1
                    else "No (Stuck with first)",
                    str(ts["count"]),
                    f"{ts['accuracy_pct']}%",
                    f"{ts['avg_seconds']}s",
                    f"{ts['avg_seconds_correct'] or 0.0}s",
                    f"{ts['avg_seconds_incorrect'] or 0.0}s",
                )
            console.print(t_time)

    if not has_rendered:
        console.print(
            "[yellow]No study history recorded yet. Complete an exam block in tutor_tui.py or tutor_cli.py to generate analytics.[/yellow]"
        )


# =====================================================================
# CLI Entrypoint
# =====================================================================


def main():
    parser = argparse.ArgumentParser(
        description="PDF-School Hybrid SQLite Analytics & Weakness Triage"
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to study.db SQLite mirror")
    parser.add_argument("--qbank", default=str(DEFAULT_QBANK), help="Path to qbank.jsonl")
    parser.add_argument("--history", default=str(DEFAULT_HISTORY), help="Path to history.jsonl")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: sync
    p_sync = subparsers.add_parser(
        "sync", help="Synchronize JSONL data into the SQLite analytical mirror"
    )
    p_sync.add_argument(
        "--force", action="store_true", help="Force complete resync regardless of mtime"
    )

    # Subcommand: report
    p_report = subparsers.add_parser("report", help="Display analytical reports")
    p_report.add_argument(
        "--type", choices=["all", "mastery", "calibration", "errors", "time"], default="all"
    )
    p_report.add_argument("--topic", help="Filter report by topic")
    p_report.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Subcommand: queue
    p_queue = subparsers.add_parser(
        "queue", help="Generate adaptive weakness remediation question queue"
    )
    p_queue.add_argument("--limit", type=int, default=15, help="Number of questions in queue")
    p_queue.add_argument("--topic", help="Filter queue by topic")

    args = parser.parse_args()
    db_p = Path(args.db)
    qb_p = Path(args.qbank)
    hi_p = Path(args.history)

    if args.command == "sync":
        counts = sync_db(db_p, qb_p, hi_p, force=args.force)
        console.print(
            f"[green]✅ Sync complete: {counts['questions']} questions, {counts['history']} history logs, {counts['fsrs']} FSRS states mirrored.[/green]"
        )

    elif args.command == "report":
        sync_db(db_p, qb_p, hi_p)
        conn = get_db_connection(db_p)
        try:
            if args.format == "json":
                payload = {
                    "mastery": get_mastery_report(conn, args.topic),
                    "calibration": get_calibration_report(conn),
                    "errors": get_error_taxonomy_report(conn, args.topic),
                    "time": get_time_analysis(conn),
                }
                print(json.dumps(payload, indent=2))
            else:
                display_reports(conn, topic=args.topic, report_type=args.type)
        finally:
            conn.close()

    elif args.command == "queue":
        questions = get_weakness_queue(db_p, qb_p, hi_p, limit=args.limit, topic=args.topic)
        if not questions:
            console.print("[yellow]No questions found matching criteria.[/yellow]")
        else:
            console.print(
                f"[bold green]Adaptive Remediation Queue ({len(questions)} items):[/bold green]"
            )
            for idx, q in enumerate(questions, 1):
                console.print(
                    f"  {idx}. [cyan]{q.id}[/cyan] | [magenta]{q.topic} - {q.subtopic or 'General'}[/magenta] | {'🔨' * q.difficulty_hammer} | {q.lead_in[:60]}..."
                )


if __name__ == "__main__":
    main()
