import json
from unittest.mock import patch

from click.testing import CliRunner

from pdf_school.cli.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "The UNIX-style agentic study engine" in result.output
    assert "doctor" in result.output
    assert "roadmap" in result.output
    assert "schedule" in result.output
    assert "sync" in result.output
    assert "tutor" in result.output


def test_cli_doctor():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "PDF-School System Diagnostics" in result.output
    assert "Python Version" in result.output
    assert "Question Bank" in result.output


def test_cli_roadmap_today():
    runner = CliRunner()
    result = runner.invoke(cli, ["roadmap", "today", "--date", "2026-09-15"])
    assert result.exit_code == 0
    assert "Study Roadmap: 2026-09-15" in result.output
    assert "Reumatología" in result.output


def test_cli_roadmap_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["roadmap", "status", "--date", "2026-09-15"])
    assert result.exit_code == 0
    assert "Roadmap Global Status" in result.output
    assert "Clínica Médica" in result.output


def test_cli_roadmap_rebalance():
    runner = CliRunner()
    result = runner.invoke(cli, ["roadmap", "rebalance", "--spread", "3", "--date", "2026-09-15"])
    assert result.exit_code == 0
    assert "track" in result.output.lower() or "redistributed" in result.output.lower()


def test_cli_schedule():
    runner = CliRunner()
    result = runner.invoke(cli, ["schedule", "--date", "2026-09-15"])
    assert result.exit_code == 0
    assert "PDF-School FSRS Scheduler" in result.output


def test_cli_sync_tsv(tmp_path):
    runner = CliRunner()
    tsv_out = str(tmp_path / "test_cards.tsv")
    result = runner.invoke(cli, ["sync", "tsv", "--output", tsv_out])
    assert result.exit_code == 0
    assert "Exported" in result.output


def test_cli_sync_db():
    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "db"])
    assert result.exit_code == 0


def test_cli_subcommands_help():
    runner = CliRunner()
    for subcmd in ["ingest", "profile", "forge", "tutor"]:
        result = runner.invoke(cli, [subcmd, "--help"])
        assert result.exit_code == 0
        assert "Usage: " in result.output


def test_cli_ingest_and_profile(tmp_path):
    runner = CliRunner()
    doc_txt = tmp_path / "lecture.txt"
    doc_txt.write_text("1. Question?\nA. 1\nB. 2\nC. 3\nD. 4\nE. 5\n", encoding="utf-8")

    result = runner.invoke(cli, ["ingest", str(doc_txt)])
    assert result.exit_code == 0

    out_prof = tmp_path / "profile.json"
    result_prof = runner.invoke(
        cli, ["profile", "--input", str(doc_txt), "--output", str(out_prof)]
    )
    assert result_prof.exit_code == 0
    assert out_prof.exists()


def test_cli_forge(tmp_path):
    runner = CliRunner()
    chunk_file = tmp_path / "chunks.jsonl"
    qb_file = tmp_path / "qbank.jsonl"
    chunk_data = {
        "chunk_id": "chunk_cli",
        "source_file": "test.pdf",
        "page_start": 1,
        "page_end": 1,
        "text": "Medical notes",
    }
    chunk_file.write_text(json.dumps(chunk_data) + "\n", encoding="utf-8")

    mock_q = {
        "id": "q_cli_01",
        "topic": "Pharmacology",
        "vignette": "A patient takes a drug...",
        "lead_in": "Which enzyme is inhibited?",
        "options": {"A": "Enzyme A", "B": "Enzyme B"},
        "correct_key": "A",
        "educational_objective": "Drug inhibits Enzyme A.",
        "distractor_analysis": {"A": "Correct", "B": "Incorrect"},
    }

    with patch("pdf_school.engine.qbank_forge.generate_structured_json", return_value=mock_q):
        result = runner.invoke(
            cli, ["forge", "--chunk-file", str(chunk_file), "--count", "1", "--qbank", str(qb_file)]
        )
        assert result.exit_code == 0
        assert qb_file.exists()


def test_cli_tutor_cli_mode():
    runner = CliRunner()
    with patch("pdf_school.tui.cli_runner.run_question_session") as mock_run:
        result = runner.invoke(cli, ["tutor", "--cli-mode", "--count", "1"])
        assert result.exit_code == 0
        assert mock_run.called
