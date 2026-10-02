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
uv run pytest --cov --cov-report=term-missing
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

Two tiers, and neither substitutes for the other.

**Per commit** — lint, format, types, and only the tests that commit touches.
Seconds. `mypy` does most of the work: a commit importing something a later commit
adds fails the type check in isolation, by name and line, with nothing executed.

**Before a push** — the whole suite with the coverage gate, once, over the final
tree. This is the one that decides.

Four things the cheap tier cannot do, all found by using it:

- Run it in the working tree, not a `git worktree`. An editable install resolves
  `practice` to the path it was installed from, so a worktree runs the *working
  tree's* source against the *commit's* tests.
- The tree must be clean. An untracked file from a later commit survives
  `git checkout` and contaminates the run.
- **The commit it blames is not necessarily the commit at fault**, because the test
  paths come from the directories a commit *touches*. Re-run the failing files
  across the whole range to attribute a failure before amending anything.
- **After changing any user-facing string, `grep -rn` for it.** The defect this tier
  has missed in two consecutive phases is a test asserting on a message, in a
  directory the commit did not touch. `mypy` cannot see it.

**Every commit in a phase must be green on its own.** A phase's commit list is a
dependency order, and narrative order is not dependency order — check it against the
actual imports, *and* against the states the commands can reach. Reorder rather than
reaching for a `--no-verify`-shaped workaround.

## Architecture, enforced by tests

Dependencies point inward: `interface/ → application/ → domain/ ← adapters/`.
`tests/unit/test_architecture.py` AST-walks the tree and fails the build on a
violation, including a deferred import inside a function.

- `domain/` imports no adapter, no interface, and no I/O module at all.
- Only `adapters/sandbox` may import `subprocess` — the trust split (**fixtures are
  trusted code, user commands are untrusted input**) is only a split if exactly one
  place starts a process.
- Only `adapters/persistence` may import `sqlite3`.
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
which is why the 22 assertion functions are in `domain/checks/` rather than under
`adapters/`.

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
- **Content is data.** Adding an exercise under `content/` needs no code. After
  editing a fixture, regenerate with `practice fixtures --write` and review the diff
  — an unexpected line means the edit changed more history than you thought.
- `uv sync` installs; `uv run` uses the locked environment. Don't re-resolve.
