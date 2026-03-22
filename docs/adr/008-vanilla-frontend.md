# ADR-008: Vanilla HTML/CSS/JS Frontend

## Status
Accepted

## Context
The game needs a web frontend. The project philosophy is "no black boxes" — build from scratch for learning.

Options:
1. **React/Vue/Svelte** — component frameworks with build tooling
2. **HTMX** — server-rendered HTML with progressive enhancement
3. **Vanilla HTML/CSS/JS** — no framework, no build step, ES modules

## Decision
Use vanilla HTML, CSS, and JavaScript (ES modules). Static files served directly by FastAPI. No npm, no webpack, no bundler.

## Consequences

**Positive:**
- Zero build step — edit a file, refresh the browser
- No node_modules, no package.json, no bundler configuration
- Consistent with the project's educational philosophy
- Every line of frontend code is visible and understandable
- FastAPI serves static files directly — one Python process for everything
- Lightweight: the entire frontend is ~6 JS files, 1 CSS file, 1 HTML file

**Negative:**
- No component reuse abstractions (no JSX, no template syntax)
- Manual DOM manipulation instead of reactive data binding
- No tree-shaking or minification (negligible for this scale)
- State management is ad-hoc (global variables) rather than stores/signals

**Mitigated by:**
- The UI is fundamentally simple: a chat interface with sidebars
- JS modules provide clean file-level separation of concerns
- CSS custom properties provide theming without preprocessors
