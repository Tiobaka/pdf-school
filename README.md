# PDF-School 📚

An agentic, UNIX-style study suite that transforms your lecture slides, syllabi, and textbooks into personalized, high-yield question banks, spaced-repetition schedules, and interactive study suites via modular CLI tools.

See the complete architectural design and technical specification in [**`PROPOSAL.md`**](PROPOSAL.md).

---

## Key Capabilities
- **Two-Track Question Forging**:
  - **Track A (Professor Style Alignment)**: Drop previous quizzes or old exams into `sources/past_exams/`, and the engine clones your professor's exact testing style, question length, distractor tricks, and slide-level focus.
  - **Track B (Pedagogical Mastery Mode)**: Grounded in cognitive psychology (desirable difficulties, 2nd-order mechanisms, competitive differential lures, refutational feedback, and contrasting case matrices).
- **Interactive Visual TUI & CLI Examination**:
  - Full graphical terminal interface built with **Textual** (`tools/tutor_tui.py` or `tools/tutor_cli.py --tui`).
  - **Dynamic Theme Switching**: Press `t` to cycle between standard themes (**Dracula, Monokai, Solarized Dark, Solarized Light, Nord, Gruvbox, Catppuccin Mocha, Tokyo Night**). Persists your preference across sessions.
  - Split-screen layout: question vignette on the left, tabbed educational breakdown, source chunk peek, question navigator, and **standard medical lab reference values** on the right.
- **Cognitive Diagnostics**: Categorizes errors into *Knowledge Gap*, *Misconception*, or *Execution Error* for tailored remediation.
- **FSRS-5 Spaced Repetition & Anki Bridge**: Modern memory modeling and zero-friction AnkiConnect sync.

---

## Directory Structure
- `sources/`: Place your raw PDF textbooks, lecture slides, and syllabi here.
  - `sources/past_exams/`: Place old quizzes, sample tests, and past exams here for style profiling.
- `content/`: Extracted text chunks, provenance metadata, and figures (`content/figures/`).
- `data/`: Question banks (`qbank.jsonl`), style profiles (`exam_style.json`), user telemetry (`history.jsonl`), and schedules (`schedule.json`).
- `tools/`: Small, single-purpose CLI utilities for extraction, profiling, generation, scheduling, and testing.
- `tests/`: Automated unit and integration test suite.
- `PROPOSAL.md`: Detailed system architecture, data schemas, and implementation roadmap.

---

## Quick Start Guide

### 1. Set Up Environment & LLM Backend
```bash
# Clone and enter directory
cd /home/archvm/projects/pdf-school

# Set your preferred LLM key (or create a .env file)
echo "GEMINI_API_KEY=your_key_here" > .env
# or: echo "OPENAI_API_KEY=sk-..." > .env
# or: echo "OPENAI_BASE_URL=http://localhost:11434/v1" > .env (Ollama / local)
```

### 2. Ingest Course Materials
```bash
# Ingest PDF, PPTX, or DOCX slides
tools/extract.py sources/lecture_slides.pptx
```

### 3. (Optional) Profile Professor Past Exams
```bash
# Analyze old quizzes for Track A style alignment
tools/profile_exam.py --input sources/past_exams/
```

### 4. Forge High-Yield Questions
```bash
# Auto-forge 10 questions using the active LLM backend
tools/qbank_forge.py auto-forge --chunk-file content/lecture_slides_chunks.jsonl --count 10
```

### 5. Launch the Visual Examination TUI
```bash
# Launch Textual TUI (Press 't' to cycle themes: Dracula, Monokai, Solarized, Nord...)
tools/tutor_tui.py
# or: tools/tutor_cli.py --tui
```


