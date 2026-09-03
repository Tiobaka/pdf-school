#!/usr/bin/env python3
"""
tutor_tui.py - High-yield, visual Terminal User Interface for PDF-School.
Built with Textual. Features split-screen examination, dynamic theme switching
(Monokai, Dracula, Solarized, Nord, Gruvbox, Catppuccin), distractor elimination,
instant source peek, and medical lab reference values.
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
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    Markdown,
    OptionList,
    ProgressBar,
    RadioButton,
    RadioSet,
    Static,
    TabbedContent,
    TabPane,
)

sys.path.insert(0, str(PROJECT_ROOT))
from tools.schemas import HistoryRecord, QBankQuestion
from tools.tutor_cli import load_qbank, log_history

# Standard themes supported by Textual
AVAILABLE_THEMES = [
    "dracula",
    "monokai",
    "solarized-dark",
    "solarized-light",
    "nord",
    "gruvbox",
    "catppuccin-mocha",
    "tokyo-night",
]

CONFIG_PATH = PROJECT_ROOT / "data" / "config.json"
DEFAULT_QBANK = str(PROJECT_ROOT / "data" / "qbank.jsonl")
DEFAULT_HISTORY = str(PROJECT_ROOT / "data" / "history.jsonl")



def load_saved_theme() -> str:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                theme = data.get("theme")
                if theme in AVAILABLE_THEMES:
                    return theme
        except Exception:
            pass
    return "dracula"


def save_theme(theme_name: str):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    current_data = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            current_data = {}
    current_data["theme"] = theme_name
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(current_data, f, indent=2)


MEDICAL_LAB_VALUES_MD = """
### 🩸 Standard Medical Lab Reference Values

| Test | Conventional Units | SI Units |
| :--- | :--- | :--- |
| **Sodium (Na⁺)** | 135–145 mEq/L | 135–145 mmol/L |
| **Potassium (K⁺)** | 3.5–5.0 mEq/L | 3.5–5.0 mmol/L |
| **Chloride (Cl⁻)** | 96–106 mEq/L | 96–106 mmol/L |
| **Bicarbonate (HCO₃⁻)** | 22–28 mEq/L | 22–28 mmol/L |
| **BUN** | 7–20 mg/dL | 2.5–7.1 mmol/L |
| **Creatinine (Cr)** | 0.6–1.2 mg/dL | 53–106 µmol/L |
| **Fasting Glucose** | 70–99 mg/dL | 3.9–5.5 mmol/L |
| **Calcium (Ca²⁺)** | 8.5–10.5 mg/dL | 2.15–2.55 mmol/L |
| **Hemoglobin (Hb)** | M: 13.5–17.5 / F: 12.0–15.5 g/dL | M: 135–175 / F: 120–155 g/L |
| **WBC Count** | 4,500–11,000 /mm³ | 4.5–11.0 × 10⁹/L |
| **Platelets** | 150,000–450,000 /mm³ | 150–450 × 10⁹/L |
| **pH (Arterial)** | 7.35–7.45 | 7.35–7.45 |
| **PaCO₂** | 35–45 mmHg | 4.7–6.0 kPa |
| **PaO₂** | 80–100 mmHg | 10.6–13.3 kPa |
"""


class TutorTUIApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #header-bar {
        height: 3;
        background: $surface;
        padding: 0 1;
        align-vertical: middle;
        border-bottom: solid $primary;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    #question-pane {
        width: 55%;
        height: 100%;
        border-right: solid $primary;
        padding: 1;
    }

    #sidebar-pane {
        width: 45%;
        height: 100%;
        padding: 1;
    }

    #vignette-box {
        height: auto;
        max-height: 50%;
        border: round $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #options-container {
        height: auto;
        margin-top: 1;
    }

    .option-btn {
        width: 100%;
        margin-bottom: 1;
        text-align: left;
    }

    .eliminated {
        text-style: strike;
        opacity: 50%;
    }

    .correct-choice {
        background: $success;
        color: $text;
        text-style: bold;
    }

    .wrong-choice {
        background: $error;
        color: $text;
        text-style: bold;
    }

    #action-bar {
        height: 3;
        margin-top: 1;
        layout: horizontal;
        align-horizontal: center;
    }

    #action-bar Button {
        margin-right: 1;
    }

    #status-pill {
        background: $accent;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    #theme-pill {
        background: $secondary;
        color: $text;
        padding: 0 1;
        margin-left: 1;
    }

    #timer-pill {
        margin-left: 1;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("t", "cycle_theme", "Theme"),
        Binding("n", "next_question", "Next"),
        Binding("p", "prev_question", "Prev"),
        Binding("v", "toggle_source", "Source"),
        Binding("l", "toggle_labs", "Labs"),
        Binding("f", "flag_question", "Flag"),
        Binding("x", "eliminate_choice", "Eliminate"),
        Binding("1", "select_opt('A')", "A", show=False),

        Binding("2", "select_opt('B')", "B", show=False),
        Binding("3", "select_opt('C')", "C", show=False),
        Binding("4", "select_opt('D')", "D", show=False),
        Binding("5", "select_opt('E')", "E", show=False),
        Binding("a", "select_opt('A')", "A", show=False),
        Binding("b", "select_opt('B')", "B", show=False),
        Binding("c", "select_opt('C')", "C", show=False),
        Binding("d", "select_opt('D')", "D", show=False),
        Binding("e", "select_opt('E')", "E", show=False),
        Binding("enter", "submit_choice", "Submit"),
    ]

    def __init__(
        self,
        questions: List[QBankQuestion],
        mode: str = "tutor",
        history_path: str = "data/history.jsonl",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.questions = questions
        self.mode = mode
        self.history_path = history_path
        self.current_idx = 0
        self.user_answers: Dict[int, str] = {}
        self.submitted: Dict[int, bool] = {}
        self.eliminated_options: Dict[int, Set[str]] = {i: set() for i in range(len(questions))}
        self.flagged: Set[int] = set()
        self.start_times: Dict[int, float] = {0: time.time()}
        self.confidence_ratings: Dict[int, str] = {}
        self.current_theme_idx = 0

    def on_mount(self):
        saved = load_saved_theme()
        if saved in AVAILABLE_THEMES:
            self.theme = saved
            self.current_theme_idx = AVAILABLE_THEMES.index(saved)
        else:
            self.theme = "dracula"
        self.set_interval(1.0, self.update_timer)
        self.refresh_question_view()

    def update_timer(self):
        timer_widget = self.query_one("#timer-pill", Label)
        elapsed = int(time.time() - self.start_times.get(self.current_idx, time.time()))
        mins, secs = divmod(elapsed, 60)
        timer_widget.update(f"⏱ {mins:02d}:{secs:02d}")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="header-bar"):
            yield Label(f"Question 1 of {len(self.questions)}", id="q-counter-pill")
            yield Label(f"Mode: {self.mode.upper()}", id="status-pill")
            yield Label(f"Theme: {self.theme}", id="theme-pill")
            yield Label("⏱ 00:00", id="timer-pill")
            yield Label("", id="q-topic-badge")

        with Horizontal(id="main-container"):
            # Left Pane: Question & Choices
            with Vertical(id="question-pane"):
                with VerticalScroll(id="vignette-box"):
                    yield Markdown("", id="vignette-markdown")
                yield Static("", id="leadin-label")
                with Vertical(id="options-container"):
                    yield Button("", id="opt-btn-A", classes="option-btn")
                    yield Button("", id="opt-btn-B", classes="option-btn")
                    yield Button("", id="opt-btn-C", classes="option-btn")
                    yield Button("", id="opt-btn-D", classes="option-btn")
                    yield Button("", id="opt-btn-E", classes="option-btn")
                with Horizontal(id="action-bar"):
                    yield Button("Submit (Enter)", id="btn-submit", variant="primary")
                    yield Button("Eliminate (x)", id="btn-strike", variant="default")
                    yield Button("Flag (f)", id="btn-flag", variant="warning")
                    yield Button("Next ❯ (n)", id="btn-next", variant="default")

            # Right Pane: Tabs for Breakdown, Source Chunk, and Lab Reference
            with Vertical(id="sidebar-pane"):
                with TabbedContent(id="tabs-view"):
                    with TabPane("Breakdown", id="tab-breakdown"):
                        with VerticalScroll():
                            yield Markdown("Submit your answer to view the pedagogical breakdown.", id="breakdown-md")
                    with TabPane("Source Peek", id="tab-source"):
                        with VerticalScroll():
                            yield Markdown("", id="source-md")
                    with TabPane("Lab Values", id="tab-labs"):
                        with VerticalScroll():
                            yield Markdown(MEDICAL_LAB_VALUES_MD)
                    with TabPane("Navigator", id="tab-nav"):
                        with VerticalScroll():
                            yield Static("Question Overview", id="nav-summary")

        yield Footer()

    def action_cycle_theme(self):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(AVAILABLE_THEMES)
        new_theme = AVAILABLE_THEMES[self.current_theme_idx]
        self.theme = new_theme
        save_theme(new_theme)
        self.query_one("#theme-pill", Label).update(f"Theme: {new_theme}")
        self.notify(f"Theme changed to: {new_theme}", timeout=2)

    def refresh_question_view(self):
        if not self.questions:
            return

        q = self.questions[self.current_idx]
        if self.current_idx not in self.start_times:
            self.start_times[self.current_idx] = time.time()

        # Update Header
        self.query_one("#q-counter-pill", Label).update(f"Question {self.current_idx + 1} of {len(self.questions)}")
        topic_text = f" [{q.topic} - {q.subtopic or 'General'}] {'🔨' * q.difficulty_hammer}"
        self.query_one("#q-topic-badge", Label).update(topic_text)

        # Update Flagged appearance
        flag_btn = self.query_one("#btn-flag", Button)
        if self.current_idx in self.flagged:
            flag_btn.label = "🚩 Flagged (f)"
            flag_btn.variant = "error"
        else:
            flag_btn.label = "Flag (f)"
            flag_btn.variant = "warning"

        # Update Vignette & Lead-in
        self.query_one("#vignette-markdown", Markdown).update(q.vignette)
        self.query_one("#leadin-label", Static).update(f"**{q.lead_in}**")

        # Update Options in-place
        is_submitted = self.submitted.get(self.current_idx, False)
        chosen = self.user_answers.get(self.current_idx)
        eliminated = self.eliminated_options.get(self.current_idx, set())

        for key in ["A", "B", "C", "D", "E"]:
            btn = self.query_one(f"#opt-btn-{key}", Button)
            if key in q.options:
                btn.display = True
                btn.label = f"({key}) {q.options[key]}"
                btn.remove_class("eliminated")
                btn.remove_class("correct-choice")
                btn.remove_class("wrong-choice")
                btn.variant = "default"

                if key in eliminated:
                    btn.add_class("eliminated")
                if chosen == key:
                    btn.variant = "primary"

                if is_submitted and self.mode == "tutor":
                    if key == q.correct_key:
                        btn.add_class("correct-choice")
                    elif key == chosen:
                        btn.add_class("wrong-choice")
            else:
                btn.display = False


        # Update Source Tab Content
        src_ref = q.source_ref
        src_md = f"### 📖 Source Provenance\n- **Document:** `{src_ref.get('source_file', 'N/A')}`\n- **Page/Slide:** {src_ref.get('page', 'N/A')}\n- **Chunk ID:** `{src_ref.get('chunk_id', 'N/A')}`\n\n*(Press `v` anytime to review this tab)*"
        self.query_one("#source-md", Markdown).update(src_md)

        # Update Breakdown Tab
        breakdown_widget = self.query_one("#breakdown-md", Markdown)
        if is_submitted:
            self.render_breakdown_markdown(q, chosen, breakdown_widget)
        else:
            breakdown_widget.update("*(Select your choice and press Submit to view the educational objective, refutational feedback, and contrasting differential matrix)*")

        # Update Navigator
        nav_summary = "### 📋 Question Navigator\n"
        for i, ques in enumerate(self.questions):
            status = "⚪ Unattempted"
            if i in self.submitted:
                c = self.user_answers.get(i)
                status = "🟢 Correct" if c == ques.correct_key else "🔴 Incorrect"
            if i in self.flagged:
                status += " 🚩"
            cursor = "👉 " if i == self.current_idx else "   "
            nav_summary += f"{cursor}**Q{i+1}:** {status} ({ques.topic})\n"
        self.query_one("#nav-summary", Static).update(nav_summary)

    def render_breakdown_markdown(self, q: QBankQuestion, chosen: Optional[str], widget: Markdown):
        is_correct = (chosen == q.correct_key)
        banner = "## ✅ CORRECT!" if is_correct else f"## ❌ INCORRECT (You selected {chosen}, Correct is {q.correct_key})"

        refutation_block = ""
        if not is_correct and chosen and chosen in q.refutational_hints:
            refutation_block = f"\n> [!WARNING]\n> **Refutation for Option ({chosen}):**\n> {q.refutational_hints[chosen]}\n"

        distractor_block = "\n### 🔍 Distractor Analysis\n"
        for k in sorted(q.options.keys()):
            analysis = q.distractor_analysis.get(k, "No explanation provided.")
            prefix = "✔" if k == q.correct_key else "✖"
            distractor_block += f"- **({k}) {prefix}**: {analysis}\n"

        comp_table_block = ""
        if q.comparison_table:
            comp_table_block = f"\n### ⚖️ Differential Comparison Table\n{q.comparison_table}\n"

        objective_block = f"\n### 🎯 Educational Objective (Takeaway Anchor)\n**{q.educational_objective}**\n"

        full_md = f"{banner}\n{objective_block}{refutation_block}{distractor_block}{comp_table_block}"
        widget.update(full_md)

    def action_select_opt(self, key: str):
        if self.submitted.get(self.current_idx, False):
            return
        q = self.questions[self.current_idx]
        if key in q.options:
            self.user_answers[self.current_idx] = key
            self.refresh_question_view()

    def action_submit_choice(self):
        if self.submitted.get(self.current_idx, False):
            return

        chosen = self.user_answers.get(self.current_idx)
        if not chosen:
            self.notify("Please select an option before submitting.", severity="warning")
            return

        self.submitted[self.current_idx] = True
        q = self.questions[self.current_idx]
        is_correct = (chosen == q.correct_key)

        elapsed = round(time.time() - self.start_times.get(self.current_idx, time.time()), 1)
        record = HistoryRecord(
            question_id=q.id,
            selected_key=chosen,
            correct_key=q.correct_key,
            is_correct=is_correct,
            time_spent_seconds=elapsed,
            confidence_rating="educated_guess",
        )
        log_history(record, self.history_path)

        self.refresh_question_view()
        # Switch tab to breakdown automatically
        tabs = self.query_one("#tabs-view", TabbedContent)
        tabs.active = "tab-breakdown"

        if is_correct:
            self.notify("Correct answer! Review explanation on the right.", severity="information")
        else:
            self.notify(f"Incorrect. Single best answer is ({q.correct_key}).", severity="error")

    def action_eliminate_choice(self):
        chosen = self.user_answers.get(self.current_idx)
        if chosen:
            eliminated = self.eliminated_options[self.current_idx]
            if chosen in eliminated:
                eliminated.remove(chosen)
                self.notify(f"Restored option ({chosen})", timeout=2)
            else:
                eliminated.add(chosen)
                self.notify(f"Eliminated option ({chosen})", timeout=2)
            self.refresh_question_view()
        else:
            self.notify("Select an option first to eliminate it.", severity="warning")

    def action_next_question(self):
        if self.current_idx < len(self.questions) - 1:
            self.current_idx += 1
            self.refresh_question_view()
        else:
            self.notify("You have reached the last question.", severity="information")

    def action_prev_question(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.refresh_question_view()

    def action_toggle_source(self):
        tabs = self.query_one("#tabs-view", TabbedContent)
        tabs.active = "tab-source"

    def action_toggle_labs(self):
        tabs = self.query_one("#tabs-view", TabbedContent)
        tabs.active = "tab-labs"

    def action_flag_question(self):
        if self.current_idx in self.flagged:
            self.flagged.remove(self.current_idx)
            self.notify("Question unflagged.")
        else:
            self.flagged.add(self.current_idx)
            self.notify("Question flagged for review! 🚩")
        self.refresh_question_view()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-submit":
            self.action_submit_choice()
        elif btn_id == "btn-next":
            self.action_next_question()
        elif btn_id == "btn-flag":
            self.action_flag_question()
        elif btn_id == "btn-strike":
            self.action_eliminate_choice()
        elif btn_id == "opt-btn-":
            pass
        elif btn_id.startswith("opt-btn-"):
            opt_key = btn_id.replace("opt-btn-", "")
            self.action_select_opt(opt_key)



def main():
    parser = argparse.ArgumentParser(description="PDF-School Visual Terminal Examination Suite (Textual TUI)")
    parser.add_argument("--qbank", default=DEFAULT_QBANK, help="Path to qbank.jsonl")
    parser.add_argument("--history", default=DEFAULT_HISTORY, help="Path to history.jsonl")
    parser.add_argument("--mode", choices=["tutor", "timed"], default="tutor", help="Exam mode")
    parser.add_argument("--count", type=int, default=15, help="Number of questions in session")

    args = parser.parse_args()
    questions = load_qbank(args.qbank)
    if not questions:
        # Provide rich demonstration questions so the TUI works out-of-the-box
        questions = [
            QBankQuestion(
                id="demo_renal_001",
                topic="Nephrology",
                subtopic="Diuretic Pharmacology",
                difficulty_hammer=3,
                cognitive_level="2nd_order_application",
                vignette="A 64-year-old male with a history of congestive heart failure (NYHA Class III) and chronic kidney disease (baseline creatinine 1.8 mg/dL) presents to the emergency department with worsening dyspnea, orthopnea, and 3+ bilateral lower extremity edema. Physical examination reveals jugular venous distension to the angle of the jaw and diffuse bilateral crackles in the lung bases. Vital signs: BP 154/92 mmHg, HR 98 bpm, RR 24/min, SpO2 89% on ambient air.",
                lead_in="Which of the following pharmacotherapeutic interventions is the most appropriate next step in management?",
                options={
                    "A": "Intravenous Furosemide",
                    "B": "Oral Hydrochlorothiazide",
                    "C": "Oral Spironolactone",
                    "D": "Intravenous Acetazolamide",
                },
                correct_key="A",
                educational_objective="Intravenous loop diuretics (e.g., furosemide) are first-line for acute decompensated heart failure due to rapid venodilation and potent natriuresis via inhibition of the luminal Na+/K+/2Cl- cotransporter in the thick ascending limb.",
                distractor_analysis={
                    "A": "Correct: IV loop diuretics produce immediate pulmonary venodilation (within 5-15 minutes) followed by potent diuresis, effective even with reduced GFR.",
                    "B": "Incorrect: Thiazides act on the distal convoluted tubule and are largely ineffective as monotherapy when GFR is significantly reduced; additionally, oral onset is too slow for acute pulmonary edema.",
                    "C": "Incorrect: Aldosterone antagonists reduce long-term mortality in HFrEF but have a delayed clinical onset (days) and confer significant hyperkalemia risk in acute decompensation with CKD.",
                    "D": "Incorrect: Acetazolamide inhibits carbonic anhydrase in the proximal tubule; it is a weak diuretic primarily used for metabolic alkalosis or altitude sickness, not acute pulmonary edema.",
                },
                refutational_hints={
                    "B": "You selected (B) Hydrochlorothiazide. While thiazides are excellent first-line antihypertensives, oral administration is too slow for acute decompensation, and thiazides lose efficacy when GFR is below 30-40 mL/min.",
                    "C": "You selected (C) Spironolactone. Spironolactone is a mainstay for long-term chronic HFrEF survival, but it has zero role in acute emergent volume unloading due to its delayed genomic mechanism of action.",
                    "D": "You selected (D) Acetazolamide. Acetazolamide induces proximal bicarbonate wasting; its natriuretic potency is insufficient to treat acute cardiogenic pulmonary edema.",
                },
                comparison_table="| Diuretic Class | Nephron Segment | Molecular Target | Efficacy in Low GFR |\n|---|---|---|---|\n| Loop (Furosemide) | Thick Ascending Limb | Na+/K+/2Cl- (NKCC2) | High (preferred) |\n| Thiazide (HCTZ) | Distal Convoluted Tubule | Na+/Cl- (NCC) | Diminished |\n| K+-Sparing (Spironolactone) | Cortical Collecting Duct | Aldosterone Receptor | Risk of Hyperkalemia |",
                source_ref={"source_file": "DEMO MODE (Ingest course PDFs into sources/ to build your bank)", "page": "1", "chunk_id": "demo_renal_ch4"},
            ),
            QBankQuestion(
                id="demo_cardio_002",
                topic="Cardiology",
                subtopic="Ischemic Heart Disease",
                difficulty_hammer=4,
                cognitive_level="3rd_order_synthesis",
                vignette="A 58-year-old female presents to the emergency room with severe retrosternal chest pressure radiating to her left jaw that began 75 minutes ago while shoveling snow. She has a history of type 2 diabetes mellitus. Initial ECG reveals 3 mm ST-segment elevations in leads II, III, and aVF with reciprocal ST depressions in I and aVL. The nearest primary percutaneous coronary intervention (PCI) facility is located 25 minutes away.",
                lead_in="Which of the following is the most appropriate definitive reperfusion strategy?",
                options={
                    "A": "Transfer for primary percutaneous coronary intervention within 90-120 minutes",
                    "B": "Immediate intravenous thrombolytic therapy with tenecteplase",
                    "C": "Subcutaneous low-molecular-weight heparin with delayed elective angiography",
                    "D": "Oral verapamil and sublingual nitroglycerin alone",
                },
                correct_key="A",
                educational_objective="Primary PCI is the preferred reperfusion strategy for acute STEMI when door-to-balloon time can be achieved within 120 minutes of first medical contact.",
                distractor_analysis={
                    "A": "Correct: Since the PCI center is 25 minutes away, total ischemic time is well under the 120-minute guideline cutoff where PCI remains superior to fibrinolytics.",
                    "B": "Incorrect: Fibrinolytic therapy is indicated only when anticipated delay to primary PCI exceeds 120 minutes from first medical contact.",
                    "C": "Incorrect: Anticoagulation is adjunctive; definitive mechanical reperfusion cannot be delayed in acute STEMI.",
                    "D": "Incorrect: Nitrates provide symptom relief but do not achieve coronary reperfusion.",
                },
                refutational_hints={
                    "B": "You selected (B) Thrombolytic therapy. Although thrombolytics can be given quickly, guidelines dictate that if transfer to a PCI facility can be accomplished within 120 minutes, primary PCI produces significantly lower rates of re-infarction, stroke, and mortality.",
                },
                comparison_table="| Modality | Door-to-Action Target | Key Indication | Major Hazard |\n|---|---|---|---|\n| Primary PCI | < 90-120 min | First-line STEMI | Vascular access complication |\n| Fibrinolysis | < 30 min (door-to-needle) | STEMI when PCI > 120 min | Intracranial hemorrhage |",
                source_ref={"source_file": "DEMO MODE (Ingest course PDFs into sources/ to build your bank)", "page": "1", "chunk_id": "demo_stemi_reperfusion"},
            ),
        ]

    app = TutorTUIApp(
        questions=questions[:args.count],
        mode=args.mode,
        history_path=args.history,
    )
    app.run()


if __name__ == "__main__":
    main()

