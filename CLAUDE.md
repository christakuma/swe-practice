# swe-practice — working notes for Claude

An offline practice environment for data-structure katas and operational git.
**The core bet: grade the end state, not the answer text.** A git exercise builds a
real repository with a real problem in it, you run real git commands, and grading
inspects the resulting repo state against declarative assertions.

**The design lives in [docs/PLAN.md](docs/PLAN.md), and it is the source of truth —
not this file.** Its status banner says where the project is; §11 holds the phase
plan; §16 is a revision log of what each phase actually found. Decisions that were
expensive to reverse are in [docs/adr/](docs/adr/) with the rejected alternatives,
which is usually the half worth reading. Read the relevant §§ before starting a
phase; this file only covers the conventions you would otherwise have to derive.

## Commands

```bash
uv run ruff check .                        # lint
uv run ruff format --check .               # format (use `ruff format .` to fix)
uv run mypy                                # strict, over src/ and tests/
uv run pytest --cov --cov-report=term-missing -n 4 --dist loadfile
```

Those four are what CI runs, on Linux **and** Windows. Two more it also runs:

```bash
uv run practice validate                   # audits the library, executes nothing
uv run practice fixtures --check           # fixture hashes vs content/fixtures.lock
```

Markers are applied by directory in `tests/conftest.py`, so `-m unit`, `-m
integration`, `-m content` and `-m e2e` follow the layout under `tests/` and no test
can fall out of every selector by being forgotten.

## Verifying work (PLAN.md §11)

One fast tier, one gate, and **no `git checkout` anywhere**.

**Per commit**, on the working tree:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q --no-cov <the tests this change touches>
```

Seconds. For content, the second line is `-m content -k <slug>` — about four
seconds per exercise.

**Before a push** — the whole suite with the coverage gate, once. This is the one
that decides, and it is what CI runs on both platforms:

```bash
uv run pytest --cov --cov-report=term-missing -n 4 --dist loadfile
```

**Four workers, not `-n auto`.** Every worker spawns its own subprocesses — a
bash fixture, a dozen `git` calls, a `pytest` per kata — so the useful worker
count tracks subprocess load rather than cores. Measured on this twelve-core
machine, with the coverage gate:

| workers | time | stable? |
|---|---|---|
| serial | 10m10s | yes |
| `-n 4` | **7m20s** | yes |
| `-n auto` (12) | 3m42s / 7m36s / 8m41s | **no** — and one run failed |

`-n auto` thrashes: the times swing by a factor of two and one run breached a
kata's wall-clock time limit, which the suite grades against on purpose. Four is
faster on average *and* repeatable. `--dist loadfile` so every test in a file
lands on one worker, which is what keeps the content suite's module-scoped
workspaces and memoised verdicts shared rather than rebuilt per worker.

Not in `addopts`, deliberately: four workers to run one file is slower than one,
and the fast tier runs one file. `-n0` turns it off.

**There is no "every commit must be green on its own" rule.** There was until
Phase 11, enforced by a loop that checked out every commit and re-ran its tests;
it was dropped because it cost more than bisectability is worth here, could not
see a content commit at all, and was re-running work the pre-push suite runs
anyway. §11 has the full reasoning. What survives is the weaker and still useful
claim: **a commit list is a dependency order** — check it against the actual
imports, because narrative order is not dependency order, and `mypy` names a
missing import for free.

Three things the fast tier cannot do:

- **Nothing else may be running.** Two pytest runs compete for temp dirs, SQLite
  files and subprocesses, and `--cov` makes it worse — one `.coverage` in the
  project root, shared. A run started beside another reports failures that do
  not reproduce. Suspect this before debugging one.
- **After changing any user-facing string, `grep -rn` for it.** The defect this
  tier reliably misses is a test asserting on a message, in a directory the
  change did not touch. `mypy` cannot see it.
- **A content change is only covered by `-m content` and `tests/e2e`.** Phase
  11's one escaped defect was a library that grew past the number of rows the
  dashboard offers, which only the e2e suite could see. When the full suite
  catches something, push the claim down into the fastest suite that can hold
  it — that one is now a content test.

## Architecture, enforced by tests

Dependencies point inward: `interface/ → application/ → domain/ ← adapters/`.
`tests/unit/test_architecture.py` AST-walks the tree and fails the build on a
violation, including a deferred import inside a function.

- `domain/` imports no adapter, no interface, and no I/O module at all.
- Only `adapters/sandbox` may import `subprocess` — the trust split (**fixtures are
  trusted code, user commands are untrusted input**) is only a split if exactly one
  place starts a process.
- Only `adapters/persistence` and `adapters/sql` may import `sqlite3` — the
  first is the app's storage, the second is the SQL drill engine, which keeps no
  schema and builds an in-memory database per grading pass. A third entry has to
  be argued for in `test_architecture.py`, where the list and the reasons live
  together ([ADR 0019](docs/adr/0019-sql-drills-as-a-third-exercise-kind.md)).
- `composition.py` is the single wiring point and the only cross-layer import.
  `Services` holds **ports, not implementations**, so mypy checks adapter conformance
  at the one place it can.

Two rules that shape what to add:

- **A port needs ≥2 real or test implementations** (§13), or it gets deleted. A
  protocol nothing has had to satisfy has not been shown to work.
- **Don't add an abstraction that forwards one call unchanged.** The fastest way to
  ruin this project is interfaces added because they look impressive.

The coverage gate covers `domain/` and `application/` only — 90% required, currently
**100%** statement and branch. That is where the correctness-critical code lives,
which is why the assertion functions are in `domain/` rather than under
`adapters/`: **20 git assertions in `domain/checks/` over `RepoQuery`, and 10 SQL
ones in `domain/drills/` over `DrillQuery`.**

**Two vocabularies, deliberately disjoint**, so a drill naming `tree_equals` is a
schema rejection rather than a check that reaches a dispatcher holding the wrong
port. What they share is everything that is not a vocabulary — `CheckSpec`,
`CheckResult`, `CheckReport`, `Params`, `compare`, `matcher`, `suggest_from` — and
the dispatcher's three jobs. `domain/drills/registry.py` has the argument.

Twenty git assertions, not twenty-two: Phase 11 deleted `reflog_contains` and
`command_count` after 24 git scenarios wanted neither. Ten drill assertions, and
`tests/content/test_drills.py` holds every one of them to being named by a
shipped drill. Both are §13's rule about abstractions earning their keep being
applied rather than quoted — add the eleventh with the exercise that wants it.

## Writing code here

**Module and class docstrings carry the reasoning, not a restatement of the name.**
This is the most distinctive thing about the codebase and the thing to match: say
why the module exists, which alternative was rejected and why, and what finding
produced the current shape. Cite PLAN.md sections (`§8.1`) where the rule lives
there. A one-line summary docstring on a module that made a real decision is
underwritten for this repo.

Comments earn their place the same way. `# Only now, and only on this path` above a
`dispose()` call is worth more than three lines describing the call.

Deliberate duplication is a pattern here, not a smell — the aggregate refuses to
*reach* an impossible state, the schema refuses to *store* one, the adapter refuses
to *execute* a disallowed command. When you add a layer to one of those, say which
job it is doing.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/) — `feat(db):`,
`test(content):`, `refactor:`, `docs:`. The history is part of the portfolio, so the
**body matters**: lead with the decision, bold the claim, and name the alternative
you rejected and why. Findings that changed the plan go in the body *and* in
PLAN.md §16. See `git log` for the register.

Commit or push only when asked.

## Finishing a phase

A phase ends with a `docs:` commit that:

1. adds any ADR the phase earned — copy `docs/adr/template.md`, next number up,
   never reuse a number, and add it to **both** indexes (`docs/adr/README.md` and
   PLAN.md §12);
2. updates PLAN.md's status banner and records the exit criteria as met, with which
   test meets each;
3. adds a §16 revision-log entry: what the phase found, what deviated from the plan
   and why, the final test count and coverage;
4. brings README.md current.

## Gotchas

- **Line endings.** `.gitattributes` declares LF everywhere, because fixture commit
  hashes must be byte-identical across platforms. Python's text mode on Windows
  writes CRLF, so pass `newline="\n"` when a script writes a tracked file.
- **Tests must never touch real storage.** An autouse fixture in `tests/conftest.py`
  points `PRACTICE_DATABASE_PATH` at a per-test path; pass `--workspace-root`
  explicitly in CLI tests. A suite that wrote to the real cache would collide with
  an open session, and `practice gc` would report test leftovers as real attempts.
- **Content is data.** Adding an exercise under `content/` needs no code — but it
  does need a line in `content/curriculum.yaml`, which `practice validate`
  requires to name every exercise exactly once ([ADR 0014](docs/adr/0014-a-hand-ordered-curriculum-manifest.md)).
  After editing a fixture, regenerate with `practice fixtures --write` and review
  the diff — an unexpected line means the edit changed more history than you
  thought.
- **Three authoring constraints that are not obvious.** `|<>&;` are rejected
  anywhere in a `.cmds` line, *including inside quotes*, so file content a
  solution writes cannot contain them — this does **not** apply to a drill's
  `.sql`, which needs semicolons and is not a command list. A fixture must leave
  a clean worktree, so no scenario can start mid-conflict — the solver runs the
  merge. And a drill's expected rows are compared as **text**: `NULL` is spelled
  as the word, a float is formatted with `%g` rather than rounded, and a drill
  whose answer is an average should ask for `ROUND(..., 2)` in SQL, because
  controlling the precision of what you return is the lesson.
- **Run the content, do not read it.** Every drill bug in Phase 14 — a vacuous
  `LIMIT`, a counter-example that returned the reference's rows, a query plan
  that scanned the other table — was invisible on the page and obvious the
  moment `-m content` ran. `uv run pytest -q --no-cov -m content -k <slug>` is
  about four seconds.
- `uv sync` installs; `uv run` uses the locked environment. Don't re-resolve.
