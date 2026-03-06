# Cursor Configuration

This folder contains Cursor rules, commands, and skills for the emagrecimento project.

## Rules (`.cursor/rules/`)

| File | Scope | Description |
|------|-------|-------------|
| `core-standards.mdc` | Always | Language, architecture, conventions |
| `python-clean-arch.mdc` | `src/**/*.py` | Python and Clean Architecture |
| `frontend.mdc` | `static/**/*`, `templates/**/*` | JS, HTML, CSS conventions |
| `tests.mdc` | `tests/**/*` | Test structure and patterns |

## Commands (`.cursor/commands/`)

Type `/` in the chat to see available commands:

| Command | Description |
|--------|-------------|
| `/run-tests` | Run pytest and fix failures |
| `/add-pdf-metric` | Add new metric from Withings PDF |
| `/code-review` | Code review checklist |
| `/start-server` | Start Flask dev server |
| `/extract-cli` | Run CLI extract script |

## Skills (`.cursor/skills/`)

Skills teach the agent specialized workflows:

| Skill | When to use |
|-------|-------------|
| `emagrecimento-workflows` | Adding metrics, use cases, UI blocks |
| `pdf-parser-patterns` | Defining regex for PDF extraction |

## Quick Start

1. Open the project in Cursor.
2. Rules apply automatically based on open files.
3. Type `/` to run a command.
4. See `AGENTS.md` in project root for full agent guide.
