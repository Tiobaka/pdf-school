import pymupdf

from pdf_school.core.extract import (
    extract_office_with_markitdown,
    extract_pdf_with_pymupdf4llm,
)


def test_extract_pdf_with_pymupdf4llm(tmp_path):
    pdf_path = tmp_path / "pharmacology.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        "# Antihypertensive Agents\n\nACE inhibitors prevent the conversion of angiotensin I to angiotensin II.",
    )
    doc.save(str(pdf_path))
    doc.close()

    out_dir = tmp_path / "content"
    fig_dir = tmp_path / "figures"

    chunks = extract_pdf_with_pymupdf4llm(pdf_path, out_dir, fig_dir, target_chunk_words=10)
    assert len(chunks) >= 1
    assert "Antihypertensive" in chunks[0].text
    assert (out_dir / "pharmacology_chunks.jsonl").exists()


def test_extract_office_with_markitdown(tmp_path):
    txt_path = tmp_path / "lecture_notes.txt"
    txt_path.write_text(
        "# Cardiology Notes\n\nAortic stenosis presents with a crescendo-decrescendo systolic ejection murmur.",
        encoding="utf-8",
    )

    out_dir = tmp_path / "content"
    chunks = extract_office_with_markitdown(txt_path, out_dir, target_chunk_words=5)

    assert len(chunks) >= 1
    assert "Cardiology Notes" in chunks[0].text
    assert (out_dir / "lecture_notes_chunks.jsonl").exists()
