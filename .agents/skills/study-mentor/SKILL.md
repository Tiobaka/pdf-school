---
name: study-mentor
description: Autonomous study director that orchestrates document ingestion, professor exam style profiling, high-yield question forging, weakness triage, and FSRS spaced repetition.
---

# Study-Mentor Skill

This skill turns any AI agent (Antigravity, OpenCode, Crush, Claude Code, Cursor, Warp) into an autonomous academic study director and clinical tutor.

## When to Activate
Activate this skill when the user:
- Asks to study, review, or prepare for an exam using notes or slides in `sources/`.
- Asks to turn a PDF or lecture slide deck into high-yield practice questions.
- Asks to analyze past tests or emulate a professor's exam style.
- Asks for today's daily review block or spaced repetition schedule.
- Requests weakness triage or remediation based on past question errors.

---

## The Standard Study Workflow

### Step 1: Content Ingestion
When new lecture slides, syllabi, or textbook chapters arrive in `sources/`:
```bash
tools/extract.py sources/<filename>
```
*Note: Handles `.pdf` (via `pymupdf4llm` with layout, markdown tables, and figures) and `.docx`, `.pptx`, `.xlsx` (via Microsoft `markitdown`).*

### Step 2: Exam Style Profiling (Track A vs. Track B)
If the student provides past quizzes or sample questions in `sources/past_exams/`:
```bash
tools/profile_exam.py --input sources/past_exams/
```
- If sample exams exist $\rightarrow$ Track A (Professor Style Alignment) is activated in `data/exam_style.json`.
- If no past exams exist $\rightarrow$ Track B (Pedagogical Mastery Mode) is used automatically (enforcing 2nd-order scenarios, competitive differential lures, refutational feedback, and contrasting case tables).

### Step 3: Question Forging
To generate questions automatically from extracted chunks:
```bash
tools/qbank_forge.py auto-forge --chunk-file content/<stem>_chunks.jsonl --count 10
```
Or to forge questions directly inside the agent context:
1. Build prompt: `tools/qbank_forge.py build-prompt --chunk-file content/<stem>_chunks.jsonl --chunk-index 0`
2. Audit question with clinical/subject expertise (e.g. `attending-physician`).
3. Ingest validated JSON: `tools/qbank_forge.py ingest '<json_string>'`

### Step 4: Spaced Repetition Scheduling
To compute memory stability and generate today's study block:
```bash
tools/scheduler.py
```
Outputs today's due reviews and new curriculum questions to `data/schedule.json`.

### Step 5: Terminal Examination & Telemetry
To start an interactive study session:
```bash
tools/tutor_cli.py --mode tutor
```
Telemetry, confidence ratings, and error classifications (*Knowledge Gap*, *Misconception*, *Execution Error*) are automatically appended to `data/history.jsonl`.

### Step 6: Weakness Triage & Remedial Forging
When the user asks *"What are my weak areas?"* or *"Drill my mistakes"*:
1. Inspect `data/history.jsonl` for questions where `is_correct == False`.
2. Group mistakes by `error_category` and `topic`.
3. Locate the source chunks in `content/` corresponding to those concepts.
4. Forge 3–5 targeted remedial questions addressing the exact misconceptions identified.
5. Sync high-yield takeaways to Anki: `tools/anki_bridge.py sync` or `tools/anki_bridge.py tsv`.
