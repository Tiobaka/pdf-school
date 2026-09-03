#!/usr/bin/env python3
"""
extract.py - Multi-format extractor for PDF-School.
Leverages pymupdf4llm for high-fidelity PDF/table/image extraction and
Microsoft MarkItDown for Word (.docx), PowerPoint (.pptx), Excel (.xlsx).
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
import hashlib
import json
from typing import List, Optional

import pymupdf4llm
from markitdown import MarkItDown
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(PROJECT_ROOT))
from tools.schemas import ContentChunk

console = Console()



def extract_pdf_with_pymupdf4llm(
    pdf_path: Path,
    output_dir: Path,
    figures_dir: Path,
    target_chunk_words: int = 500,
) -> List[ContentChunk]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Use pymupdf4llm for native layout analysis, markdown tables, and figure cropping
    pages_data = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        write_images=True,
        image_path=str(figures_dir),
        image_format="png",
        table_output="markdown",
    )

    doc_stem = pdf_path.stem
    chunks: List[ContentChunk] = []

    current_words: List[str] = []
    current_page_start = 1
    current_figures: List[str] = []
    current_section: Optional[str] = None

    for page_idx, page_info in enumerate(pages_data):
        page_num = page_idx + 1
        page_text = page_info.get("text", "").strip()
        if not page_text:
            continue

        # Extract image links embedded in markdown
        import re
        img_matches = re.findall(r"!\[.*?\]\((.*?)\)", page_text)
        current_figures.extend(img_matches)

        # Detect headers for section titles
        headers = re.findall(r"^#+\s+(.+)$", page_text, re.MULTILINE)
        if headers and current_section is None:
            current_section = headers[0].strip()

        words = page_text.split()
        current_words.extend(words)

        if len(current_words) >= target_chunk_words or page_idx == len(pages_data) - 1:
            combined_text = " ".join(current_words)
            chunk_hash = hashlib.sha256(f"{doc_stem}_{current_page_start}_{page_num}_{combined_text[:60]}".encode()).hexdigest()[:12]
            chunk_id = f"{doc_stem}_p{current_page_start}-{page_num}_{chunk_hash}"

            chunk = ContentChunk(
                chunk_id=chunk_id,
                source_file=str(pdf_path),
                page_start=current_page_start,
                page_end=page_num,
                section_title=current_section,
                text=combined_text,
                figures=list(dict.fromkeys(current_figures)),
            )
            chunks.append(chunk)

            current_words = []
            current_figures = []
            current_page_start = page_num + 1
            current_section = None

    # Write JSONL
    out_file = output_dir / f"{doc_stem}_chunks.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch.model_dump(), ensure_ascii=False) + "\n")

    return chunks


def extract_office_with_markitdown(
    file_path: Path,
    output_dir: Path,
    target_chunk_words: int = 500,
) -> List[ContentChunk]:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_stem = file_path.stem

    md = MarkItDown()
    result = md.convert(str(file_path))
    raw_markdown = result.text_content

    paragraphs = raw_markdown.split("\n\n")
    chunks: List[ContentChunk] = []

    current_words: List[str] = []
    chunk_index = 1
    current_section: Optional[str] = None

    import re
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue

        headers = re.findall(r"^#+\s+(.+)$", p_clean, re.MULTILINE)
        if headers and current_section is None:
            current_section = headers[0].strip()

        words = p_clean.split()
        current_words.extend(words)

        if len(current_words) >= target_chunk_words:
            combined_text = " ".join(current_words)
            chunk_hash = hashlib.sha256(f"{doc_stem}_{chunk_index}_{combined_text[:60]}".encode()).hexdigest()[:12]
            chunk_id = f"{doc_stem}_chunk{chunk_index}_{chunk_hash}"

            chunk = ContentChunk(
                chunk_id=chunk_id,
                source_file=str(file_path),
                page_start=chunk_index,
                page_end=chunk_index,
                section_title=current_section,
                text=combined_text,
                figures=[],
            )
            chunks.append(chunk)

            current_words = []
            current_section = None
            chunk_index += 1

    if current_words:
        combined_text = " ".join(current_words)
        chunk_hash = hashlib.sha256(f"{doc_stem}_{chunk_index}_{combined_text[:60]}".encode()).hexdigest()[:12]
        chunk_id = f"{doc_stem}_chunk{chunk_index}_{chunk_hash}"
        chunk = ContentChunk(
            chunk_id=chunk_id,
            source_file=str(file_path),
            page_start=chunk_index,
            page_end=chunk_index,
            section_title=current_section,
            text=combined_text,
            figures=[],
        )
        chunks.append(chunk)

    out_file = output_dir / f"{doc_stem}_chunks.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch.model_dump(), ensure_ascii=False) + "\n")

    return chunks


def process_file_or_dir(
    target_path_str: str,
    output_dir_str: str = "content",
    figures_dir_str: str = "content/figures",
    chunk_size: int = 500,
):
    target = Path(target_path_str)
    out_dir = Path(output_dir_str)
    fig_dir = Path(figures_dir_str)

    if not target.exists():
        console.print(f"[red]Error: Target '{target_path_str}' does not exist.[/red]")
        sys.exit(1)

    files_to_process = []
    if target.is_file():
        files_to_process.append(target)
    else:
        for ext in ["*.pdf", "*.docx", "*.pptx", "*.xlsx", "*.txt", "*.md"]:
            files_to_process.extend(target.glob(ext))

    if not files_to_process:
        console.print(f"[yellow]No supported documents found in '{target_path_str}'.[/yellow]")
        return

    table = Table(title="📚 PDF-School Ingestion Report", show_header=True, header_style="bold green")
    table.add_column("File", style="cyan")
    table.add_column("Engine", style="magenta")
    table.add_column("Chunks", justify="right", style="bold")
    table.add_column("Output File", style="dim")

    for f in files_to_process:
        ext = f.suffix.lower()
        if ext == ".pdf":
            chunks = extract_pdf_with_pymupdf4llm(f, out_dir, fig_dir, target_chunk_words=chunk_size)
            table.add_row(f.name, "PyMuPDF4LLM (Layout & Tables)", str(len(chunks)), f"{f.stem}_chunks.jsonl")
        elif ext in [".docx", ".pptx", ".xlsx", ".txt", ".md"]:
            chunks = extract_office_with_markitdown(f, out_dir, target_chunk_words=chunk_size)
            table.add_row(f.name, "Microsoft MarkItDown", str(len(chunks)), f"{f.stem}_chunks.jsonl")

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Multi-format document extractor (PDF, DOCX, PPTX) for PDF-School")
    parser.add_argument("target", help="Path to document file or directory")
    parser.add_argument("--output-dir", default="content", help="Directory for chunk JSONL files")
    parser.add_argument("--figures-dir", default="content/figures", help="Directory for extracted images")
    parser.add_argument("--chunk-size", type=int, default=500, help="Target word count per chunk")

    args = parser.parse_args()
    process_file_or_dir(args.target, args.output_dir, args.figures_dir, args.chunk_size)


if __name__ == "__main__":
    main()
