from pathlib import Path
from tools.anki_bridge import export_to_tsv
from tools.schemas import QBankQuestion


def test_export_to_tsv(tmp_path):
    tsv_out = tmp_path / "deck.tsv"
    q = QBankQuestion(
        id="q_immuno_01",
        topic="Immunology",
        vignette="A patient with recurrent bacterial infections...",
        lead_in="What immunoglobulin is deficient?",
        options={"A": "IgA", "B": "IgG", "C": "IgM"},
        correct_key="B",
        educational_objective="IgG deficiency predisposes to encapsulated bacterial infections.",
        distractor_analysis={"A": "Mucosal", "B": "Correct", "C": "Primary response"},
    )
    count = export_to_tsv([q], str(tsv_out))

    assert count == 1
    assert tsv_out.exists()
    content = tsv_out.read_text(encoding="utf-8")
    assert "Immunology" in content
    assert "IgG deficiency" in content
    assert "\t" in content
