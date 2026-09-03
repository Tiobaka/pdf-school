# PDF-School 📚

An agentic, UNIX-style study suite that transforms your lecture slides, syllabi, and textbooks into personalized, high-yield question banks, spaced-repetition schedules, and interactive study suites via modular CLI tools.

See the complete architectural design and technical specification in [**`PROPOSAL.md`**](PROPOSAL.md).

---

## Key Capabilities
- **Two-Track Question Forging**:
  - **Track A (Professor Style Alignment)**: Drop previous quizzes or old exams into `sources/past_exams/`, and the engine clones your professor's exact testing style, question length, distractor tricks, and slide-level focus.
  - **Track B (Pedagogical Mastery Mode)**: Grounded in cognitive psychology (desirable difficulties, 2nd-order mechanisms, competitive differential lures, refutational feedback, and contrasting case matrices).
- **Interactive CLI Examination**: Fast, focused terminal test runner featuring Tutor Mode, Timed Block Mode, metacognitive calibration, and 1-key source peek back to the exact lecture slide/textbook chunk.
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

## Quick Start
When starting an Antigravity CLI session in this repository:
```bash
cd /home/archvm/projects/pdf-school
agy
```

