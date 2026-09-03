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
            app.action_select_opt("B")
            assert app.user_answers[0] == "B"

            # Test submit
            app.action_submit_choice()
            assert app.submitted[0] is True
            assert hist_file.exists()

    asyncio.run(run_headless())
