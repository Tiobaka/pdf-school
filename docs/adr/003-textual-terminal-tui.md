# ADR 003: Terminal Textual TUI vs. Web GUI

## Status
Accepted

## Context
High-stakes study and clinical test preparation demand uninterrupted, deep focus. Web applications often introduce high latency, browser distraction, network dependency, heavy framework overhead (Electron/React/Node), and security/privacy concerns with local notes.

## Decision
We build the primary visual user interface using **Textual** (Python's asynchronous Terminal User Interface framework):
- Split-screen layout: Question vignette on the left; tabbed educational breakdown, source chunk peek, question navigator, medical reference values, and daily roadmap on the right.
- Live theme switching (Dracula, Monokai, Nord, Gruvbox, Tokyo Night, Solarized Dark/Light) with instant persistence.
- Keyboard-driven interaction (`1`-`5` for options, `x` for distractor elimination, `f` for flag, `n`/`p` for navigation).
- Fallback headless CLI mode (`pdf-school tutor --cli-mode`) for low-spec or ssh/tmux environments.

## Consequences
### Positive
- Instant startup (<100ms) with zero browser or web server dependencies.
- Distraction-free, pure keyboard workflow optimized for deep work.
- Operates seamlessly over remote SSH, Docker containers, and tmux multiplexers.

### Negative
- Cannot display complex animated WebGL graphics or arbitrary interactive HTML elements without terminal image protocols (e.g. Kitty/Sixel).
