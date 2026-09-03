# Project Proposal: PDF-School

> **The UNIX-Style Agentic Study Engine**  
> *Transforming arbitrary PDF curricula into personalized, UWorld/Bootcamp-grade question banks, spaced-repetition schedules, and interactive study suites via modular CLI tools.*

---

## 1. Executive Summary & Vision

High-stakes learning platforms like **UWorld**, **Med School Bootcamp**, and **Amboss** are renowned for their pedagogical effectiveness: multi-step scenario vignettes, comprehensive distractor rationales, educational objectives, and dynamic scheduling. However, they suffer from two major flaws:
1. **Proprietary & Rigid**: You cannot ingest your own institution's lecture notes, custom syllabi, or specialized textbooks.
2. **Monolithic SaaS Lock-in**: Your data is locked behind recurring subscriptions, opaque algorithms, and closed web portals.

**PDF-School** replaces this monolithic model with the **UNIX Philosophy**:
*Write small, specialized programs that do one task well. Handle plain text / JSON Lines as the universal interface. Compose them with an Antigravity agent acting as conductor.*

---

## 2. Architecture & Data Flow

```
                     ┌──────────────────┐
                     │   Source PDFs    │ (Textbooks, Syllabi, Slides)
                     └────────┬─────────┘
                              │
                      [1. pdf-extract]
                              │
                              ▼
                     ┌──────────────────┐
                     │ Markdown Chunks  │ (Normalized sections & tables)
                     └────────┬─────────┘
                              │
                      [2. qbank-forge]  <--- Supervised by Antigravity Agent
                              │
                              ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│3. study-scheduler│ │  qbank.jsonl     │ │  5. anki-export  │
│ (FSRS Spaced Rep)│◄┼─  (Question Bank)┼─►│  (.apkg / .tsv) │
└────────┬─────────┘ └────────┬─────────┘ └──────────────────┘
         │                    │
         └──────────┬─────────┘
                    │
             [4. tutor-cli]             <--- Interactive Terminal Test Mode
                    │
                    ▼
             [history.jsonl]            <--- Telemetry & Retention Tracking
```

---

## 3. The Modular Toolset (The UNIX Decomposition)

### Tool 1: `pdf-extract` (Content Ingestion)
- **Purpose**: Ingests textbook chapters, syllabus PDFs, or lecture slide decks.
- **Behavior**: Extracts text, tables, and section hierarchies into clean, token-efficient Markdown chunks.
- **Tech**: Python via `pymupdf` / `pdfplumber`.

### Tool 2: `qbank-forge` (Vignette & Question Generator)
- **Purpose**: Generates high-yield, vignette-style questions adhering to the pedagogical anatomy of UWorld/Bootcamp.
- **Output Schema (`qbank.jsonl`)**:
  - `id`: Deterministic hash of source topic.
  - `topic` / `subtopic`: Categorization hierarchy.
  - `vignette`: Scenario-based patient/practical case presentation.
  - `question_stem`: Clear interrogative prompt.
  - `options`: 4–5 realistic multiple-choice choices (`A` through `E`).
  - `correct_key`: The single best answer.
  - `educational_objective`: 1–2 sentence high-yield takeaway.
  - `distractor_analysis`: Granular breakdowns explaining why each wrong option is incorrect and under what circumstances it would be true.

### Tool 3: `study-scheduler` (FSRS Spaced Repetition Engine)
- **Purpose**: Generates dynamic daily study queues ("Today's Block: 15 Review + 10 New").
- **Algorithm**: Implements **FSRS (Free Spaced Repetition Scheduler)**, modeling card stability, difficulty, and retrievability based on target exam dates.
- **Input**: User study history (`history.jsonl`) and target exam milestone.

### Tool 4: `tutor-cli` (Interactive Terminal Examination Mode)
- **Purpose**: Simulates the exam interface directly inside the shell.
- **Modes**:
  - **Tutor Mode**: Immediate post-selection reveal with color-coded option breakdowns and full explanations.
  - **Timed Block Mode**: Simulates real test conditions (e.g. 40 questions in 60 minutes), rendering a score report and mistake review afterwards.
- **Telemetry**: Automatically appends results, response time, and confidence ratings to `history.jsonl`.

### Tool 5: `anki-export` (Flashcard Bridge)
- **Purpose**: Automatically generates flashcard decks from question educational objectives and missed concepts for mobile review on Anki.

---

## 4. Repository Layout

```
pdf-school/
├── sources/               # Raw PDFs (syllabi, textbooks, lecture slides)
├── content/               # Extracted Markdown chunks and notes
├── data/
│   ├── qbank.jsonl        # The master question bank
│   ├── history.jsonl      # User performance telemetry & FSRS states
│   └── schedule.json      # Active study plan & daily blocks
├── tools/
│   ├── pdf_extract.py     # Tool 1: PDF text & table extractor
│   ├── qbank_forge.py     # Tool 2: Question & vignette generator
│   ├── scheduler.py       # Tool 3: FSRS spaced-repetition scheduler
│   ├── tutor_cli.py       # Tool 4: Terminal test runner
│   └── anki_export.py     # Tool 5: Anki deck exporter
├── .agents/
│   ├── rules/
│   │   └── AGENTS.md      # Repository agent guidelines
│   └── skills/
│       └── study-mentor/  # Antigravity skill for automated study routines
├── PROPOSAL.md            # This document
└── README.md              # Project onboarding & CLI instructions
```

---

## 5. Antigravity Agent Integration

The Antigravity CLI acts as the strategic study director:
1. **Clinical / Academic Peer Review**: Leverages specialized subagents (such as `attending-physician` or domain experts) to audit question accuracy and distractor plausibility.
2. **Weakness Triage**: The agent parses `history.jsonl`, identifies knowledge blind spots, and drafts targeted remedial notes or generates extra practice questions on deficient topics.
3. **Automated Batch Processing**: Can run unattended overnight (`agy --goal`) to process an entire 400-page PDF and populate a complete 300-question bank ready for your morning study session.

---

## 6. Implementation Roadmap

- [ ] **Phase 1**: Ingestion & Question Generation (`pdf_extract.py` & `qbank_forge.py`).
- [ ] **Phase 2**: Terminal Examination Interface (`tutor_cli.py`).
- [ ] **Phase 3**: Spaced Repetition Scheduling (`scheduler.py` with FSRS).
- [ ] **Phase 4**: Anki Deck Exporter (`anki_export.py`).
- [ ] **Phase 5**: Agent Skill Integration (`study-mentor`).
