# Agent Guidelines & Repository Architecture: PDF-School

This repository is **platform-agnostic**. Whether invoked via Antigravity, OpenCode, Crush, Warp, Cursor, or raw shell, any agent or developer must adhere to the following architecture and engineering standards.

---

## 1. Universal Architecture & Philosophy
- **UNIX Philosophy**: Each tool in `tools/` is a standalone, single-purpose CLI program communicating through plain text, JSON, and JSON Lines (`.jsonl`).
- **Zero Monolithic Lock-In**: Everything runs locally. Question generation connects via `tools/llm_client.py` to any LLM backend (Gemini, OpenAI, Anthropic, OpenRouter, or local Ollama) using standard environment variables or `.env`.
- **Two-Track Pedagogical Design**:
  - **Track A (Professor Style)**: Ingests old exams from `sources/past_exams/` via `tools/profile_exam.py` to clone the professor's exact testing voice, length, and quirks.
  - **Track B (Pedagogical Mastery)**: Default cognitive science engine enforcing 2nd-order reasoning, competitive differential lures, refutational feedback, and contrasting case tables.

---

## 2. Core CLI Command Interface
Any agent can control the system via standard bash commands:

| Action | Command |
| :--- | :--- |
| **Ingest Sources** | `tools/extract.py sources/<file_or_dir>` |
| **Profile Professor Style** | `tools/profile_exam.py --input sources/past_exams/` |
| **Auto-Forge Questions** | `tools/qbank_forge.py auto-forge --chunk-file content/<chunks>.jsonl --count 5` |
| **Lint & Ingest Question** | `tools/qbank_forge.py ingest '<json_or_file>'` |
| **Calculate FSRS Queue** | `tools/scheduler.py` |
| **Launch Terminal Exam** | `tools/tutor_cli.py --mode tutor` |
| **Export/Sync Anki** | `tools/anki_bridge.py tsv` or `tools/anki_bridge.py sync` |

---

## 3. Engineering & Verification Standards
- **Verification-First**: Always run `pytest` to ensure all 19+ unit tests pass after making changes to schemas or tools.
- **Data Integrity**: Never manually corrupt or rewrite `data/qbank.jsonl` or `data/history.jsonl`. Always use schema-validated functions in `tools/qbank_forge.py` and `tools/tutor_cli.py`.
- **NBME Item-Writing Quality Gate**: Any forged question must satisfy standard NBME rules (homogeneous distractors, positive question stems, explicit distractor rationales, and 1-sentence educational objectives).
