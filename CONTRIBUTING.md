# Contributing to PDF-School 📚

Thank you for your interest in contributing to **PDF-School**! We welcome contributions from developers, students, educators, and clinicians.

---

## 1. Development Philosophy
- **UNIX Simplicity**: Build standalone, single-purpose CLI programs communicating through plain text, JSON, and JSON Lines (`.jsonl`).
- **Zero Monolithic Lock-In**: Everything runs locally and connects to any LLM backend (Gemini, OpenAI, Anthropic, OpenRouter, or local Ollama).
- **Pedagogical Rigor**: Question generation adheres strictly to NBME item-writing standards (no negative stems, homogeneous distractor lengths, positive lead-ins, 1-sentence takeaways).
- **Verification-First**: Always maintain 100% passing tests and >80% test coverage.

---

## 2. Development Setup

### Prerequisites
- Python 3.10+ (tested through Python 3.14)
- [`uv`](https://github.com/astral-sh/uv) (recommended fast package manager) or standard `pip` / `venv`

### Installation
```bash
# Clone the repository
git clone https://github.com/your-org/pdf-school.git
cd pdf-school

# Create and activate virtual environment with uv
uv venv
source .venv/bin/activate

# Install in editable mode with development dependencies
uv pip install -e ".[dev]"
```

---

## 3. Quality & Verification Standards

Before opening a pull request or completing code changes, run the full verification suite:

```bash
# 1. Format code with Ruff
ruff format .

# 2. Lint check with Ruff
ruff check .

# 3. Static type check with Mypy
mypy src/ tests/

# 4. Run automated test suite with coverage
pytest --cov=src/pdf_school --cov-report=term
```

All four commands **must pass with 0 errors**.

---

## 4. Project Layout

```
pdf-school/
├── .github/workflows/ci.yml    # Automated CI matrix (Python 3.10-3.14)
├── pyproject.toml              # Build backend, dependencies, tool configs
├── src/pdf_school/             # Core Python package
│   ├── cli/main.py             # Click CLI entrypoint (`pdf-school`)
│   ├── core/                   # Extraction, config, LLM client
│   ├── engine/                 # QBank forge, FSRS scheduler, roadmap math
│   ├── bridges/                # AnkiConnect, SQLite analytics, TSV exporter
│   ├── tui/                    # Textual interactive terminal application
│   └── schemas.py              # Pydantic data schemas & validators
├── tests/                      # Automated pytest test suite
├── docs/                       # Architecture Decision Records (ADRs) & documentation
├── data/                       # Local study data (qbank.jsonl, history.jsonl, roadmap.json)
├── content/                    # Extracted markdown chunks & figure images
└── sources/                    # Raw source PDFs, lecture slides, and past exams
```

---

## 5. Submitting a Pull Request

1. Create a feature branch: `git checkout -b feature/my-new-feature`
2. Commit your changes with a descriptive message following Conventional Commits (e.g., `feat: add PDF bookmarks parsing`, `fix: handle missing roadmap milestones`).
3. Ensure all tests and linters pass (`pytest`, `ruff check`, `mypy`).
4. Push to your branch and submit a Pull Request.
