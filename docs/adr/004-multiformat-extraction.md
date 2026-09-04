# ADR 004: Hybrid Extraction via PyMuPDF4LLM & Microsoft MarkItDown

## Status
Accepted

## Context
Academic and medical course materials span diverse, unstructured file formats:
- Dense multi-column PDF textbooks and guideline papers.
- PowerPoint slides (`.pptx`) with bullet points and embedded figures.
- Word documents (`.docx`) containing sample exam items and notes.
- Spreadsheets (`.xlsx`) with diagnostic tables.

Standard text extraction libraries often strip tables into garbled text, lose column layout, or drop embedded figures.

## Decision
We implement a hybrid multi-format document extraction pipeline:
1. **PDFs**: Parsed via `pymupdf4llm` to preserve layout geometry, extract markdown formatted tables, and extract cropped high-resolution figure images with page provenance.
2. **Office Files (`.docx`, `.pptx`, `.xlsx`)**: Parsed via Microsoft's `markitdown` engine into structured Markdown.
3. **Normalization**: All documents are partitioned into semantic chunks with provenance metadata (`chunk_id`, `source_file`, `page_start`, `page_end`, `figures`) saved to `content/<name>_chunks.jsonl`.

## Consequences
### Positive
- High-fidelity extraction preserving diagnostic comparison tables and anatomical diagrams.
- Consistent downstream input for both LLM question forging and Professor Style profiling.
- Single unified command: `pdf-school ingest <file_or_dir>`.

### Negative
- Requires `pymupdf` and `markitdown` dependencies in the installation footprint.
