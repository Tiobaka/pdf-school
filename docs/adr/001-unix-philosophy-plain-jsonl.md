# ADR 001: UNIX Philosophy & Plain JSONL Storage

## Status
Accepted

## Context
Educational platforms and test preparation systems often use proprietary databases, monolithic backends, or cloud-hosted database servers (PostgreSQL, MongoDB). In contrast, `pdf-school` is designed for privacy, local-first operation, transparency, git version control, and modular UNIX CLI composition (`grep`, `jq`, `sed`, `awk`, `cat`).

## Decision
We adopt **JSON Lines (`.jsonl`)** as the primary storage format for the question bank (`data/qbank.jsonl`) and telemetry logs (`data/history.jsonl`), accompanied by a read-only SQLite sync layer (`study.db`) for analytical reporting.

- Each line is a self-contained, schema-validated JSON document representing a single question or review record.
- Appending new items is an $O(1)$ atomic filesystem operation.
- The entire dataset can be diffed, merged, and version-controlled via standard Git.

## Consequences
### Positive
- **Zero Monolithic Lock-In**: Data is 100% human-readable and inspectable with basic shell tools.
- **Git-Native Sync**: Users can backup, branch, and sync study materials across machines without cloud databases.
- **Resilience**: A corrupted line does not corrupt the rest of the database; parsers can skip malformed entries gracefully.

### Negative
- Complex multi-table relational queries require loading records into memory or running `pdf-school sync db` to build the derived SQLite projection.
