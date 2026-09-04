#!/usr/bin/env python3
"""
pdf_extract.py - Layout-aware PDF and lecture slide extractor for PDF-School.
Extracts structured markdown chunks, provenance metadata, and embedded figures.
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
if _venv_python.exists() and sys.prefix != str(PROJECT_ROOT / ".venv"):
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

sys.path.insert(0, str(PROJECT_ROOT))
from tools.extract import extract_pdf_with_pymupdf4llm
from tools.schemas import ContentChunk


def extract_pdf_chunks(
    pdf_path: str,
    output_dir: str = "content",
    figures_dir: str = "content/figures",
    target_chunk_words: int = 500,
    min_image_size: int = 100,
) -> list[ContentChunk]:
    """Compatibility wrapper that delegates to extract.py's PyMuPDF4LLM engine."""
    p_path = Path(pdf_path)
    if not p_path.exists():
        raise FileNotFoundError(f"Source file not found: {pdf_path}")

    return extract_pdf_with_pymupdf4llm(
        p_path,
        Path(output_dir),
        Path(figures_dir),
        target_chunk_words=target_chunk_words,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Layout-aware PDF and slide extractor for PDF-School"
    )
    parser.add_argument("pdf_path", help="Path to raw source PDF file")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "content"),
        help="Directory for extracted chunks JSONL",
    )
    parser.add_argument(
        "--figures-dir",
        default=str(PROJECT_ROOT / "content" / "figures"),
        help="Directory for extracted images",
    )
    parser.add_argument("--chunk-size", type=int, default=500, help="Target word count per chunk")

    args = parser.parse_args()
    try:
        chunks = extract_pdf_chunks(
            args.pdf_path,
            output_dir=args.output_dir,
            figures_dir=args.figures_dir,
            target_chunk_words=args.chunk_size,
        )
        print(f"✅ Successfully extracted {len(chunks)} chunks from {args.pdf_path}")
        print(f"📁 Chunks saved to: {args.output_dir}/{Path(args.pdf_path).stem}_chunks.jsonl")
    except Exception as e:
        print(f"❌ Extraction error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
