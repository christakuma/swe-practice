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

**Status:** Phase 4 (kata engine) complete — **a kata is solvable from the
terminal.** `practice solve` starts an attempt, provisions a workspace, runs the
exercise's hidden test suite in a pinned, isolated subprocess, and prints a
verdict in which each test is one check and each check is labelled with the
sentence its author wrote. Underneath it: the composition root, the first two
use cases, and an attempt aggregate that enforces its own lifecycle.

Git scenarios still cannot be graded — a fixture builds a real repo and real
commands run against it, but the assertion engine that inspects the end state is
Phase 5, and asking for one says so rather than guessing. See
[docs/PLAN.md](docs/PLAN.md) for the full design and the phase plan, and
[docs/adr/](docs/adr/) for the decisions and the alternatives that were
rejected.

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

## Solving a kata

```bash
uv run practice solve katas/two-sum --source my-solution.py --time "O(n)" --space "O(n)"
```

Each test in the hidden suite becomes one check, labelled with its docstring, so
a failure reads as a sentence about what the solution must do rather than as a
function name. The declared complexity is **compared and never graded** — static
Big-O analysis of arbitrary code is not something this tool pretends to do — so
a claim that disagrees with the exercise's expectation is an *advisory*: you
passed, and here is the thing to reconcile.

With no `--source`, it grades the exercise's own stub, which fails every check.
That is the intended first run: a hidden suite that passes an unimplemented stub
grades nothing, and `tests/content/test_katas.py` holds every kata in the
library to both halves of that.

It exits 0 on a pass (advisories included — the goal was met either way), 1 when
a required check fails, and 2 when the attempt could not be run at all. Start
and submit are one command on purpose at this phase: attempts live in memory
until the SQLite store lands in Phase 6, so an attempt cannot outlive the
process that created it.

## Checking the exercise library

```bash
uv run practice validate
```

Reports every problem in every exercise in one pass, located to the field, and
exits non-zero if anything is wrong — so CI depends on it. It runs nothing, so
it works on a machine with no git, and it prints what a passing run does **not**
prove.

```bash
uv run practice fixtures --check
```

Runs every fixture and compares the commit hashes it produced against
`content/fixtures.lock`. CI runs this on Linux *and* Windows, which is how
cross-platform determinism is tested rather than asserted: a disagreement names
which platform diverged. After editing a fixture, regenerate with
`--write` and review the diff.

```bash
uv run practice gc
```

Reports the attempt workspaces left on disk. It never deletes anything yet, on
purpose — an orphan is *a workspace with no active attempt row*, and the attempt
table lands in Phase 6. Until then "collect orphans" could delete a session you
have open.

## Layout

```
src/practice/
├── domain/        pure data and functions; zero I/O
│   └── checks/    the assertion vocabulary, as pure functions over a port
├── application/   use cases over ports, and the exercise-kind registry
├── adapters/      sandbox, kata engine, content, in-memory attempts
├── interface/     FastAPI + HTMX web app, Typer CLI
├── composition.py the single wiring point; the only cross-layer import
└── config.py      where the library and the workspaces live
content/           exercises as declarative data — adding one needs no code
└── fixtures.lock  commit hashes every fixture must reproduce, on any platform
docs/adr/          architecture decision records
tests/             unit · integration · content · web · e2e
```

Dependencies point inward, and `tests/unit/test_architecture.py` fails the build
if that is ever violated — architecture that isn't tested decays. The same suite
enforces one more rule from Phase 3: only `adapters/sandbox` may import
`subprocess`. The trust split the sandbox rests on — **fixtures are trusted
code, user commands are untrusted input** — is only a split if there is exactly
one place that starts a process.
