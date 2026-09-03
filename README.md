# PDF-School 📚

An agentic, UNIX-style study suite that transforms your PDF materials into a personalized **UWorld / Bootcamp.com-grade** learning engine.

See the complete architectural design and technical specification in [**`PROPOSAL.md`**](PROPOSAL.md).

---

## Directory Structure
- `sources/`: Place your raw PDF textbooks, lecture slides, and syllabi here.
- `content/`: Extracted text chunks and study notes.
- `data/`: Question banks (`qbank.jsonl`), user test history (`history.jsonl`), and schedules (`schedule.json`).
- `tools/`: Small, single-purpose CLI utilities for extraction, generation, scheduling, and testing.
- `PROPOSAL.md`: Detailed system architecture, data schemas, and implementation roadmap.

---

## Quick Start
When starting an Antigravity CLI session in this repository:
```bash
cd /home/archvm/projects/pdf-school
agy
```
