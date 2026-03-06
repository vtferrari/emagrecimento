# Emagrecimento - Agent Guide

Quick reference for AI agents working on this project.

## Project Overview

Dashboard de Emagrecimento: web app that combines MyFitnessPal (ZIP export) and Withings (medical report PDF) to visualize cutting metrics.

## Tech Stack

- **Backend**: Python 3.10+, Flask, pandas, pypdf
- **Frontend**: Vanilla JS, Chart.js, single-page HTML/CSS
- **Architecture**: Clean Architecture (domain → application → infrastructure)

## Key Paths

| Path | Purpose |
|------|---------|
| `src/emagrecimento/domain/` | Entities, value objects. Uses pandas for ZipData DataFrames (accepted trade-off for tabular data). |
| `src/emagrecimento/application/` | Use cases, interfaces (ports), services, transformers, presenters |
| `src/emagrecimento/infrastructure/` | ZIP reader, PDF reader, PDF metrics parser |
| `src/emagrecimento/container.py` | Composition root, dependency wiring |
| `app.py` | Flask entry point |
| `static/js/app.js` | Frontend logic |
| `templates/index.html` | Dashboard HTML |

## Conventions

- **Code/comments**: English
- **User-facing text**: Portuguese (Brazil)
- **Clean Architecture**: Mandatory (domain → application → infrastructure)
- **TDD**: Red-Green-Refactor. Write tests first, then implement. Never add production code without a test.

## Common Tasks

- **Add PDF metric**: Parser → Transformer → Frontend labels → Test
- **Run tests**: `pytest -v --tb=short`
- **Start server**: `python app.py`

## Cursor Setup

- **Rules**: `.cursor/rules/*.mdc` (core, python, frontend, tests)
- **Commands**: `.cursor/commands/*.md` (type `/` in chat)
- **Skills**: `.cursor/skills/` (emagrecimento-workflows, pdf-parser-patterns)
