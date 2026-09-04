# ADR 002: FSRS-5 vs. Legacy SM-2 Spaced Repetition

## Status
Accepted

## Context
Traditional flashcard systems rely on the SuperMemo-2 (SM-2) algorithm invented in 1987. SM-2 uses fixed ease factors and heuristic interval multipliers that suffer from significant inefficiencies:
- Rigid interval growth leading to "ease hell" on challenging cards.
- Inability to account for variable retention targets.
- Poor handling of long delays or cramming sessions.

## Decision
We adopt the **Free Spaced Repetition Scheduler (FSRS-5)** (`open-spaced-repetition/fsrs`), based on modern DSR (Difficulty, Stability, Retrievability) memory dynamics:
- **Stability ($S$)**: Time (in days) for retention probability to decline from 100% to 90%.
- **Difficulty ($D$)**: Inherent conceptual resistance of the item.
- **Retrievability ($R$)**: Probability of recall at elapsed time $t$, modeled as $R(t) = \left(1 + \text{factor} \cdot \frac{t}{S}\right)^{\text{decay}}$.

The scheduler recomputes memory state dynamically by replaying `data/history.jsonl` chronologically, eliminating the need to store stale interval timers.

## Consequences
### Positive
- Statistically superior memory retention with fewer redundant reviews compared to SM-2.
- Clean chronological replay: memory state is derived deterministically from the immutable event log.
- Full interoperability with modern Anki (via Anki's native FSRS support).

### Negative
- Requires recalculating state over history logs during queue generation (mitigated by fast vector math).
