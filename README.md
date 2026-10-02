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

**Status:** Phase 5 (git scenario engine) complete — **the core bet works.**
Both exercise kinds are solvable from the terminal, and a git scenario is graded
on what your commands actually did:

```
$ practice solve git/revert-a-pushed-commit -c my-attempt.cmds
  ok   $ git reset --hard HEAD~1
         HEAD is now at dc52587 Add CSV line parser
  ok   $ git push --force origin main
  ...
  ok   The committed tree matches the state before the bad commit
  FAIL The bad commit is still reachable — you did not rewrite published history
         expected @c3 (bab6eca) reachable from HEAD (dc52587), got not reachable
         Your teammate already has c3. If it stops being an ancestor of `main`,
         their next pull either conflicts or silently reintroduces the bad commit.
  note You did not force-update a shared branch
```

That is the whole argument in one verdict. The **content check passes** — the
files are byte-identical to what a correct `git revert` produces — and the
ancestry check is what tells the two apart. A tool grading on file content
accepts this answer; a tool matching command text would have to guess which of
two dozen correct phrasings to allow.

Underneath it: 22 pure assertion functions over a read-only port, implemented
twice (real git, in-memory fake) and proved to agree by a conformance suite, and
a content suite that grades every reference solution in the library and holds
every counter-example to exactly the checks it declares. See
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

## Solving a git scenario

```bash
uv run practice solve git/revert-a-pushed-commit --commands my-attempt.cmds
```

A `.cmds` file is one command per line, `#` comments and blanks ignored — the
same format the library's own reference solutions use. Every line goes through
the real command policy: parsed into an argv, checked against the exercise's
`allowed_commands`, and run with **no shell**, so `echo x > f` is refused with a
pointer to the virtual `write` instead of silently not redirecting. Each command
is echoed with what it printed before the next one runs, so a replay reads as a
transcript rather than a wall of output and a verdict.

```bash
uv run practice solve git/revert-a-pushed-commit --reference
```

Replays the exercise's own solution, which is also exactly how CI grades it —
through the same use cases, the same policy and the same budget a solver gets.
If the rules a reference answer is validated against were not the rules a solver
is held to, a green build would mean a solution exists rather than a solution
exists *within the rules*, and a scenario could ship unsolvable
([ADR 0011](docs/adr/0011-reference-solutions-are-command-lists.md)).

There is no interactive console yet. A scenario is solved in one process for the
same reason a kata is — attempts are in memory until Phase 6 — and the
console belongs in the web workbench anyway (Phase 8).

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
│   └── checks/    the 22 assertions, as pure functions over a read-only port
├── application/   use cases over ports, and the exercise-kind registry
├── adapters/
│   ├── sandbox/   builds a repository and runs commands in it
│   ├── git/       reads one back: GitRepoQuery, ScenarioGrader
│   ├── kata/      the pytest runner and its grader
│   └── content/   the exercise library on disk
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

The assertion functions are in `domain/checks/` rather than under `adapters/`
for the same kind of reason. They are pure functions over a `RepoQuery` port and
never shell out, so putting them inside the layer the coverage gate and the
architecture test police makes "testable with no git installed" a structural
fact rather than a happy accident. All 22 are unit-tested against an in-memory
fake in milliseconds; a conformance suite then proves that fake answers the same
questions real git does, which is the only thing that makes the fast tests
evidence about anything.
