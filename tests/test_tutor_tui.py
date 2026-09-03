import asyncio
from pathlib import Path
from tools.schemas import QBankQuestion
from tools.tutor_tui import TutorTUIApp, AVAILABLE_THEMES


def test_tui_app_headless_mount_and_theme_cycling(tmp_path):
    q = QBankQuestion(
        id="q_tui_test_01",
        topic="Pharmacology",
        subtopic="Autonomics",
        vignette="A 28-year-old female presents with organophosphate toxicity...",
        lead_in="Which medication should be administered to reactivate acetylcholinesterase?",
        options={"A": "Atropine", "B": "Pralidoxime", "C": "Physostigmine", "D": "Neostigmine"},
        correct_key="B",
        educational_objective="Pralidoxime (2-PAM) reactivates phosphorylated acetylcholinesterase.",
        distractor_analysis={
            "A": "Muscarinic antagonist, does not regenerate enzyme.",
            "B": "Correct.",
            "C": "AChE inhibitor.",
            "D": "AChE inhibitor.",
        },
    )

    hist_file = tmp_path / "history.jsonl"

    async def run_headless():
        app = TutorTUIApp(
            questions=[q],
            mode="tutor",
            history_path=str(hist_file),
        )
        async with app.run_test() as pilot:
            # Check initial mount
            assert app.current_idx == 0
            assert len(app.questions) == 1

            # Cycle theme and test theme switching
            initial_theme = app.theme
            app.action_cycle_theme()
            assert app.theme != initial_theme
            assert app.theme in AVAILABLE_THEMES

            # Test option selection
            app.action_select_opt("A")
            assert app.user_answers[0] == "A"

            # Test distractor elimination (x key)
            app.action_eliminate_choice()
            assert "A" in app.eliminated_options[0]

            # Toggle eliminate again to restore
            app.action_eliminate_choice()
            assert "A" not in app.eliminated_options[0]

            # Select correct option B
            app.action_select_opt("B")
            assert app.user_answers[0] == "B"

            # Test tabs switching
            app.action_toggle_source()
            from textual.widgets import TabbedContent
            tabs = app.query_one("#tabs-view", TabbedContent)
            assert tabs.active == "tab-source"

            app.action_toggle_labs()
            assert tabs.active == "tab-labs"

            # Test submit
            app.action_submit_choice()
            assert app.submitted[0] is True
            assert hist_file.exists()
            assert tabs.active == "tab-breakdown"

    asyncio.run(run_headless())

