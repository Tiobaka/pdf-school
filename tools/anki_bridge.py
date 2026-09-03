#!/usr/bin/env python3
"""
anki_bridge.py - Flashcard exporter and AnkiConnect sync bridge for PDF-School.
Supports direct AnkiConnect live sync and fallback TSV export.
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
import html
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from rich.console import Console

sys.path.insert(0, str(PROJECT_ROOT))
from tools.schemas import QBankQuestion

DEFAULT_QBANK = str(PROJECT_ROOT / "data" / "qbank.jsonl")
DEFAULT_TSV = str(PROJECT_ROOT / "data" / "anki_cards.tsv")


console = Console()


def invoke_ankiconnect(action: str, **params) -> Dict[str, Any]:
    url = "http://localhost:8765"
    payload = json.dumps({"action": action, "params": params, "version": 6}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("error"):
                raise RuntimeError(f"AnkiConnect Error: {data['error']}")
            return data.get("result")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Could not connect to AnkiConnect at {url}. Ensure Anki is running with the AnkiConnect add-on.") from e


def load_questions(qbank_path: str = "data/qbank.jsonl") -> List[QBankQuestion]:
    questions = []
    path = Path(qbank_path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                questions.append(QBankQuestion(**json.loads(line)))
            except Exception:
                continue
    return questions


def export_to_tsv(questions: List[QBankQuestion], output_tsv: str = "data/anki_cards.tsv") -> int:
    out_path = Path(output_tsv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for q in questions:
            # Card 1: Question Vignette -> Answer & Rationale
            opts_formatted = "<br>".join([f"<b>{k})</b> {html.escape(v)}" for k, v in sorted(q.options.items())])
            front = f"<h3>[{html.escape(q.topic)}] {html.escape(q.subtopic or '')}</h3><p>{html.escape(q.vignette)}</p><p><b>{html.escape(q.lead_in)}</b></p><p>{opts_formatted}</p>"
            
            back = f"<h2 style='color:green;'>Answer: ({q.correct_key}) {html.escape(q.options.get(q.correct_key, ''))}</h2>"
            back += f"<p><b>Educational Objective:</b> {html.escape(q.educational_objective)}</p>"
            
            distractor_html = "<br>".join([f"<b>({k})</b> {html.escape(v)}" for k, v in sorted(q.distractor_analysis.items())])
            back += f"<hr><p><small>{distractor_html}</small></p>"

            # Clean tabs and newlines for TSV
            clean_front = front.replace("\t", " ").replace("\n", " ")
            clean_back = back.replace("\t", " ").replace("\n", " ")
            tags = f"PDF-School {q.topic.replace(' ', '_')}"

            f.write(f"{clean_front}\t{clean_back}\t{tags}\n")
            count += 1

    return count


def sync_to_ankiconnect(questions: List[QBankQuestion], deck_name: str = "PDF-School") -> int:
    # 1. Create deck if not exists
    invoke_ankiconnect("createDeck", deck=deck_name)

    notes = []
    for q in questions:
        opts_formatted = "<br>".join([f"<b>{k})</b> {html.escape(v)}" for k, v in sorted(q.options.items())])
        front = f"<h3>[{html.escape(q.topic)}]</h3><p>{html.escape(q.vignette)}</p><p><b>{html.escape(q.lead_in)}</b></p><p>{opts_formatted}</p>"
        
        back = f"<h2 style='color:green;'>Answer: ({q.correct_key}) {html.escape(q.options.get(q.correct_key, ''))}</h2>"
        back += f"<p><b>Takeaway:</b> {html.escape(q.educational_objective)}</p>"

        note = {
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": front,
                "Back": back,
            },
            "tags": ["PDF-School", q.topic.replace(" ", "_")],
            "options": {"allowDuplicate": False}
        }
        notes.append(note)

    results = invoke_ankiconnect("addNotes", notes=notes)
    added_count = sum(1 for r in results if r is not None)
    return added_count


def main():
    parser = argparse.ArgumentParser(description="Anki Bridge for PDF-School")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # TSV Export
    p_tsv = subparsers.add_parser("tsv", help="Export to native Anki TSV file")
    p_tsv.add_argument("--qbank", default="data/qbank.jsonl", help="Path to qbank.jsonl")
    p_tsv.add_argument("--output", default="data/anki_cards.tsv", help="Output TSV file path")

    # AnkiConnect Sync
    p_sync = subparsers.add_parser("sync", help="Push questions directly to running Anki via AnkiConnect")
    p_sync.add_argument("--qbank", default="data/qbank.jsonl", help="Path to qbank.jsonl")
    p_sync.add_argument("--deck", default="PDF-School", help="Target deck name in Anki")

    args = parser.parse_args()
    questions = load_questions(args.qbank)
    if not questions:
        console.print(f"[yellow]No questions found in '{args.qbank}'.[/yellow]")
        sys.exit(0)

    if args.command == "tsv":
        count = export_to_tsv(questions, args.output)
        console.print(f"[green]✅ Exported {count} cards to TSV at: [bold]{args.output}[/bold][/green]")
    elif args.command == "sync":
        try:
            added = sync_to_ankiconnect(questions, args.deck)
            console.print(f"[green]🎉 Successfully synced {added} cards to Anki deck '[bold]{args.deck}[/bold]'![/green]")
        except ConnectionError as ce:
            console.print(f"[red]❌ Connection failed:[/red] {ce}")
            console.print("[blue]Tip: You can always use 'tools/anki_bridge.py tsv' to export a file for manual import.[/blue]")
            sys.exit(1)


if __name__ == "__main__":
    main()
