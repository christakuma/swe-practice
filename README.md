# swe-practice

An offline practice environment for the two things entry-level engineers are
actually tested on: **data-structure problem solving** and **operational
competence with git**. Local web app — no network, no accounts, no CDN.

The core bet, in one line:

> **Grade the end state, not the answer text.**

A git exercise ships a fixture that builds a real repo with a real problem in it
— detached HEAD, a bad merge, a commit already pushed to a shared branch. You
run real git commands against it, and grading inspects the resulting repo state
against declarative assertions. So `git revert`, `git reset --hard`, and
`git checkout <sha> -- .` are judged on what they actually did, *including how
they differ*.

**Status:** Phase 2 (content model and loader) complete — the pure domain, the
Pydantic content schema, the filesystem repository, and `practice validate` over
three exercises. See [docs/PLAN.md](docs/PLAN.md) for the full design and the
phase plan, and [docs/adr/](docs/adr/) for the decisions and the alternatives
that were rejected.

## Getting started

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```bash
uv sync
```

## Checks

The same four commands CI runs, on Linux and Windows:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-report=term-missing
```

Test selection follows the directory layout under `tests/` — markers are applied
automatically, so `uv run pytest -m unit` gets the fast pure tests,
`-m integration` gets the ones that touch the filesystem, and `-m content` runs
the library checks over every exercise on disk.

## Checking the exercise library

```bash
uv run practice validate
```

Reports every problem in every exercise in one pass, located to the field, and
exits non-zero if anything is wrong — so CI depends on it. It also prints what a
passing run does **not** prove: until the sandbox lands in Phase 3, a git
scenario is structurally valid and not yet known to be solvable.

## Layout

```
src/practice/
├── domain/        pure data and functions; zero I/O
│   └── checks/    the assertion vocabulary, as pure functions over a port
├── application/   use cases over ports
├── adapters/      git, sandbox, SQLite, filesystem content
├── interface/     FastAPI + HTMX web app, Typer CLI
└── config.py      where the exercise library lives
content/           exercises as declarative data — adding one needs no code
docs/adr/          architecture decision records
tests/             unit · integration · content · web · e2e
```

Dependencies point inward, and `tests/unit/test_architecture.py` fails the build
if that is ever violated — architecture that isn't tested decays.
