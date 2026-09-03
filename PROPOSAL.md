# Project Proposal: PDF-School 2.0

> **The UNIX-Style Agentic Study Engine**  
> *Transforming arbitrary curricula and lecture materials into personalized, high-yield question banks, spaced-repetition schedules, and interactive study suites via modular CLI tools.*

---

## 1. Executive Summary & Vision

High-stakes learning platforms like **UWorld**, **Med School Bootcamp**, and **AMBOSS** are renowned for their pedagogical effectiveness: multi-step scenario vignettes, comprehensive distractor rationales, educational objectives, and dynamic scheduling. However, for a university or medical student, they suffer from fundamental misalignments:
1. **Disconnected from In-House Exams**: School professors write questions with unique idiosyncrasies—some test specific lecture slide bullet points, some focus on direct biochemical recall, others craft negative stems or custom case styles. Studying standard board questions alone does not guarantee honoring in-house class exams.
2. **Proprietary & Rigid**: You cannot ingest your institution's custom lecture notes, syllabi, or specialized textbooks.
3. **Monolithic SaaS Lock-in**: User performance data and schedules are locked behind recurring subscriptions and closed web portals.

**PDF-School** solves this with the **UNIX Philosophy**:
*Write small, specialized programs that do one task well. Handle plain text / JSON Lines as the universal interface. Compose them with an Antigravity agent acting as conductor.*

---

## 2. Architecture & Data Flow

```
                     ┌────────────────────────┐
                     │ Raw Sources & Syllabi  │ (PDFs, Slides, Handouts)
                     └───────────┬────────────┘
                                 │
                         [1. pdf-extract]
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │ Normalized Chunks &    │ (With Page/Section Provenance
                     │ Extracted Figures      │  and Embedded Images)
                     └───────────┬────────────┘
                                 │
┌────────────────────────┐       │
│  sources/past_exams/   │       │
│ (Old Quizzes & Tests)  │       │
└───────────┬────────────┘       │
            │                    │
    [2. exam-profiler]           │
            │                    │
            ▼                    │
    [exam_style.json]            │
            │                    │
            └───────────┬────────┘
                        │
                [3. qbank-forge] <--- Supervised by Antigravity Agent
                        │              Track A: Professor Style Alignment
                        │              Track B: Pedagogical Mastery Mode
                        ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│4. study-scheduler│ │  qbank.jsonl     │ │  6. anki-bridge  │
│ (FSRS Spaced Rep)│◄┼─  (Question Bank)┼─►│(AnkiConnect/APKG)│
└────────┬─────────┘ └────────┬─────────┘ └──────────────────┘
         │                    │
         └──────────┬─────────┘
                    │
             [5. tutor-cli]             <--- High-Performance Interactive CLI
                    │                        (Tutor, Timed, Metacognition,
                    │                         Refutational Feedback, Source Peek)
                    ▼
             [history.jsonl]            <--- Telemetry with Tri-Partite Error Taxonomy
```

---

## 3. The Two-Track Question Engine

### Track A: Professor Style Alignment (When Sample Exams Are Provided)
When the student uploads previous exams, quizzes, or sample questions into `sources/past_exams/`:
1. `tools/profile_exam.py` parses the exams and synthesizes `data/exam_style.json`:
   - **Stem Anatomy**: Direct recall vs. short vignettes vs. clinical cases vs. negative stems (*"All of the following EXCEPT..."*).
   - **Option Mechanics**: 4 choices (A–D), 5 choices (A–E), multiple-select, or true/false patterns.
   - **Cognitive Bias**: Does the professor test slide minutiae (exact cutoffs, specific enzyme names, named clinical trials) or conceptual synthesis?
   - **Few-Shot Exemplars**: Extracted exemplars injected into `qbank-forge` prompts to clone the professor's exact testing voice and style.

### Track B: Pedagogical Mastery Mode (Evidence-Based Cognitive Science)
When no past exams exist, `qbank-forge` defaults to cognitive science-backed question engineering:

#### 1. During Solving (Retrieval & Desirable Difficulties)
- **Desirable Difficulty (2nd-Order Mechanism)**: Scenarios connecting Clinical Clues $\rightarrow$ Pathophysiology $\rightarrow$ Pharmacological Mechanism rather than simple 1st-order factual recognition.
- **Competitive Lures (The Little & Bjork Effect)**: Distractors are realistic differential diagnoses, forcing retrieval of both target and non-target concepts ("spillover learning").
- **Metacognitive Calibration**: A confidence prompt (*Certain*, *Educated Guess*, *Blind Guess*) before answer submission to eliminate hindsight bias.

#### 2. During Breakdown (Feedback & Consolidation)
- **Refutational Feedback**: Explicitly deconstructs the student's chosen incorrect option (*"You selected B because... However, notice X..."*) to eradicate distractor intrusion.
- **Contrasting Cases Matrix**: A side-by-side differential comparison table between the correct answer and the closest distractors to build expert "illness scripts".
- **First-Principles Mechanistic Flow**: Explains the causal cascade: $\text{Receptor} \rightarrow \text{Pathway} \rightarrow \text{Physiological Effect} \rightarrow \text{Clinical Resolution}$.
- **Takeaway Anchor**: A single high-yield educational objective sentence suitable for direct Cloze deletion flashcards.

---

## 4. The Modular Toolset

### Tool 1: `pdf-extract` (Content Ingestion & Figure Extraction)
- **Purpose**: Ingests textbook chapters, syllabus PDFs, and lecture slides.
- **Behavior**: Extracts structured text, preserves tables, headers, and extracts embedded figures into `content/figures/` with source provenance anchors (`source_file`, `page_start`, `page_end`, `section_title`).

### Tool 2: `exam-profiler` (Style Analyzer)
- **Purpose**: Analyzes student-uploaded past exams and generates `data/exam_style.json` with few-shot exemplars and structural rules.

### Tool 3: `qbank-forge` (Question Generator)
- **Purpose**: Synthesizes questions adhering to either the active professor profile (Track A) or the cognitive mastery standard (Track B).
- **Output Schema (`qbank.jsonl`)**:
  - `id`: Deterministic hash.
  - `source_ref`: Chunks and exact page numbers.
  - `difficulty_hammer`: 1 to 5 scale.
  - `cognitive_level`: 1st-order recall vs. 2nd-order application vs. 3rd-order synthesis.
  - `vignette` & `lead_in`: Stem and interrogative question.
  - `options`: A–D or A–E options.
  - `correct_key`: Best answer.
  - `educational_objective`: 1-sentence high-yield anchor.
  - `distractor_analysis`: Individual rationales for each option.
  - `refutational_hints`: Targeted explanations for why each distractor is chosen and why it fails.
  - `comparison_table`: Markdown differential comparison matrix.

### Tool 4: `study-scheduler` (FSRS Spaced Repetition Engine)
- **Purpose**: Computes memory stability, difficulty, and retrievability using the **Free Spaced Repetition Scheduler (FSRS-5)**.
- **Output**: Generates targeted daily study queues (`schedule.json`).

### Tool 5: `tutor-cli` (Interactive CLI Examination Runner)
- **Purpose**: High-speed, focused terminal test runner.
- **Features**:
  - Tutor Mode (immediate refutational reveal) vs. Timed Block Mode.
  - Metacognitive confidence check.
  - Option strikethrough and flagging.
  - Instant 1-key source peek (opens the exact textbook/slide chunk).
  - Tri-Partite Error Taxonomy logging into `history.jsonl` (*Knowledge Gap*, *Misconception*, *Execution Error*).

### Tool 6: `anki-bridge` (Flashcard Sync)
- **Purpose**: Directly syncs questions and educational objectives to local Anki via **AnkiConnect API** (with `.apkg` / TSV fallback).

---

## 5. Repository Layout

```
pdf-school/
├── sources/               # Raw PDFs (syllabi, textbooks, lecture slides)
│   └── past_exams/        # Uploaded previous exams, quizzes, sample questions
├── content/               # Extracted Markdown chunks and notes
│   └── figures/           # Extracted diagrams and images
├── data/
│   ├── exam_style.json    # Extracted professor style profile (if exams provided)
│   ├── qbank.jsonl        # The master question bank
│   ├── history.jsonl      # User performance telemetry & FSRS states
│   └── schedule.json      # Active study plan & daily blocks
├── tools/
│   ├── pdf_extract.py     # Tool 1: Layout-aware extractor & figure cropper
│   ├── profile_exam.py    # Tool 2: Professor exam style analyzer
│   ├── qbank_forge.py     # Tool 3: Two-track question generator
│   ├── scheduler.py       # Tool 4: FSRS spaced-repetition scheduler
│   ├── tutor_cli.py       # Tool 5: High-performance terminal exam runner
│   └── anki_bridge.py     # Tool 6: AnkiConnect & flashcard exporter
├── tests/                 # Verification test suite for all CLI tools
├── .agents/
│   ├── rules/
│   │   └── AGENTS.md      # Repository agent guidelines
│   └── skills/
│       └── study-mentor/  # Antigravity skill for automated study routines
├── PROPOSAL.md            # System architecture specification
└── README.md              # Project onboarding & CLI instructions
```

---

## 6. Phased Implementation Roadmap

- [x] **Phase 1**: Core Data Schemas, Ingestion (`extract.py`), and Exam Profiling (`profile_exam.py`).
- [x] **Phase 2**: Two-Track Question Forging (`qbank_forge.py`) with Refutational Feedback & Comparison Tables.
- [x] **Phase 3**: Robust CLI Examination Engine (`tutor_cli.py`) with Metacognition & Error Categorization.
- [x] **Phase 4**: FSRS Spaced Repetition Scheduling (`scheduler.py`) & Telemetry Processing.
- [x] **Phase 5**: Anki Bridge (`anki_bridge.py`) with AnkiConnect live sync.
- [x] **Phase 6**: Rich Textual TUI Layer (`tutor_tui.py`) with standard themes (Dracula, Monokai, Solarized, Nord, Gruvbox).

