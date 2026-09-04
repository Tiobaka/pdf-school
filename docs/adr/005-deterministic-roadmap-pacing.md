# ADR 005: Deterministic Zero-LLM Roadmap Pacing & Dynamic Rebalancer

## Status
Accepted

## Context
When students fall behind on their study schedule due to illness, unexpected clinical shifts, or difficult topics, typical AI-based schedulers tend to hallucinate dates, drop rest days, or re-generate unpredictable timelines.

## Decision
We decouple study pacing from LLMs and implement a **purely deterministic, local mathematical pacing engine** in `pdf_school.engine.roadmap`:
1. **Immutable Roadmap Definition (`data/roadmap.json`)**: Encodes calendar days, active study days, mandatory rest days (e.g. Saturdays), daily vignette quotas, and milestone checkpoint exams.
2. **Deterministic Progress & Debt Calculation**: Reconciles target vignette quotas against verified completed questions in `data/history.jsonl` up to `as_of_date`.
3. **Dynamic Rebalancer (`pdf-school roadmap rebalance --spread N`)**:
   - Computes study deficit: $\text{Backlog} = \sum \text{Planned} - \sum \text{Completed}$.
   - Mathematically redistributes the deficit evenly across the next $N$ active study days ($\Delta = \lceil \text{Backlog} / N \rceil$).
   - Never alters rest days, past days, or future milestone dates.
   - Operates in $O(N)$ with zero network or token cost.

## Consequences
### Positive
- 100% reproducible, predictable mathematical redistribution.
- Zero token costs or LLM dependencies for daily pacing.
- Clear, unmovable boundaries protecting scheduled rest days.

### Negative
- Requires a structured initial roadmap definition (`data/roadmap.json`), either generated once from the course syllabus or provided as a template.
