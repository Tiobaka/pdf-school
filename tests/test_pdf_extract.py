import os
import tempfile
from pathlib import Path
import pymupdf
import pytest
from tools.pdf_extract import extract_pdf_chunks


def create_sample_pdf(filepath: str):
    doc = pymupdf.open()
    # Page 1
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Renal Pathology\n\nGlomerulonephritis represents an inflammatory condition...")
    # Page 2
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Pharmacology of Diuretics\n\nFurosemide is a loop diuretic that inhibits the Na+/K+/2Cl- cotransporter in the thick ascending limb of the loop of Henle.")
    doc.save(filepath)
    doc.close()


def test_pdf_extraction(tmp_path):
    pdf_file = tmp_path / "sample_lecture.pdf"
    create_sample_pdf(str(pdf_file))

    out_dir = tmp_path / "content"
    fig_dir = tmp_path / "figures"

    chunks = extract_pdf_chunks(
        str(pdf_file),
        output_dir=str(out_dir),
        figures_dir=str(fig_dir),
        target_chunk_words=10,  # Small chunk size so each page becomes a chunk
    )

    assert len(chunks) >= 1
    assert chunks[0].source_file == str(pdf_file)
    assert chunks[0].page_start == 1
    assert "Glomerulonephritis" in chunks[0].text

    jsonl_file = out_dir / "sample_lecture_chunks.jsonl"
    assert jsonl_file.exists()
