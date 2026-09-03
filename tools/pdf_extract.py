#!/usr/bin/env python3
"""
pdf_extract.py - Layout-aware PDF and lecture slide extractor for PDF-School.
Extracts structured markdown chunks, provenance metadata, and embedded figures.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import List

import pymupdf

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.schemas import ContentChunk


def extract_pdf_chunks(
    pdf_path: str,
    output_dir: str = "content",
    figures_dir: str = "content/figures",
    target_chunk_words: int = 500,
    min_image_size: int = 100,
) -> List[ContentChunk]:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"Source file not found: {pdf_path}")

    out_path = Path(output_dir)
    fig_path = Path(figures_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    fig_path.mkdir(parents=True, exist_ok=True)

    doc_stem = pdf_file.stem
    doc = pymupdf.open(str(pdf_file))
    
    chunks: List[ContentChunk] = []
    current_words: List[str] = []
    current_figures: List[str] = []
    current_page_start = 1
    current_section = None
    
    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        page = doc[page_idx]

        # Extract images from page
        image_list = page.get_images(full=True)
        page_figures = []
        for img_idx, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            width = base_image["width"]
            height = base_image["height"]

            # Filter out tiny icons, logos, bullets
            if width >= min_image_size and height >= min_image_size:
                fig_filename = f"{doc_stem}_p{page_num}_img{img_idx+1}.{image_ext}"
                fig_dest = fig_path / fig_filename
                with open(fig_dest, "wb") as f_img:
                    f_img.write(image_bytes)
                rel_fig_path = str(fig_dest.relative_to(Path.cwd())) if fig_dest.is_relative_to(Path.cwd()) else str(fig_dest)
                page_figures.append(rel_fig_path)

        # Extract text blocks with layout sorting
        # sort=True sorts blocks in reading order (top-to-bottom, left-to-right)
        blocks = page.get_text("blocks", sort=True)
        page_text_blocks = []
        for b in blocks:
            text = b[4].strip()
            if not text:
                continue
            # Simple heuristic: single-line short uppercase or title text can be a section heading
            if len(text.splitlines()) == 1 and len(text.split()) <= 8 and (text.isupper() or text.istitle()):
                if current_section is None:
                    current_section = text
            page_text_blocks.append(text)

        page_combined_text = f"### [Page {page_num}]\n" + "\n\n".join(page_text_blocks)
        page_words = page_combined_text.split()

        current_words.extend(page_words)
        current_figures.extend(page_figures)

        # If accumulated word count exceeds target or we're at the last page
        if len(current_words) >= target_chunk_words or page_num == len(doc):
            chunk_content = " ".join(current_words)
            chunk_hash = hashlib.sha256(f"{doc_stem}_{current_page_start}_{page_num}_{chunk_content[:50]}".encode()).hexdigest()[:12]
            chunk_id = f"{doc_stem}_p{current_page_start}-{page_num}_{chunk_hash}"
            
            chunk = ContentChunk(
                chunk_id=chunk_id,
                source_file=str(pdf_file),
                page_start=current_page_start,
                page_end=page_num,
                section_title=current_section,
                text=chunk_content,
                figures=list(dict.fromkeys(current_figures)),  # deduplicate
            )
            chunks.append(chunk)

            # Reset accumulator for next chunk
            current_words = []
            current_figures = []
            current_page_start = page_num + 1
            current_section = None

    doc.close()

    # Save chunks as jsonl
    jsonl_dest = out_path / f"{doc_stem}_chunks.jsonl"
    with open(jsonl_dest, "w", encoding="utf-8") as f_out:
        for ch in chunks:
            f_out.write(json.dumps(ch.model_dump(), ensure_ascii=False) + "\n")

    return chunks


def main():
    parser = argparse.ArgumentParser(description="Layout-aware PDF and slide extractor for PDF-School")
    parser.add_argument("pdf_path", help="Path to raw source PDF file")
    parser.add_argument("--output-dir", default="content", help="Directory for extracted chunks JSONL")
    parser.add_argument("--figures-dir", default="content/figures", help="Directory for extracted images")
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
