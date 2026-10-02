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

**Status:** Phase 7 (web shell and kata workbench) complete — **the core bet
works, a session survives the terminal it was opened in, and a kata is now solved
in a browser.** Both exercise kinds are solvable from the terminal, and a git
scenario is graded on what your commands actually did:

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

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13. Nothing else — no npm,
no bundler, no network.

```bash
uv sync
uv run practice serve
```

That opens the web app on `http://127.0.0.1:8765`: browse the library, start an
attempt, write a solution in the editor and read the verdict. Everything it
serves comes off the disk, so it works with the wifi off.

The terminal is a second adapter over the same use cases, documented below. It is
not a fallback — it is the proof that the core is not secretly coupled to HTTP.

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

## The web app

```bash
uv run practice serve
```

`/browse` filters the library by kind, difficulty and tag, and starts an attempt;
`/attempt/{id}` is the workbench — the prompt beside a CodeMirror editor seeded
from the exercise's stub, and a verdict panel that the submission swaps in without
a page reload. An attempt already open shows **Resume** instead of **Start**,
because a second one would split one piece of work across two budgets.

Submissions return **HTML, not JSON**. There is no API — `openapi_url=None` — and
the fragment a submission renders is the same template the page uses when it loads
an attempt that was graded last week, so a reload cannot disagree with what you
were just shown ([ADR 0007](docs/adr/0007-htmx-over-a-single-page-app.md)).

**Offline is enforced, not promised.** htmx and CodeMirror 5 are committed files
pinned by SHA-256; one test greps every template and stylesheet of ours for a
remote reference, a second checks those four files against their hashes, and a
third asserts that every file under `static/` is covered by one of the two —
because the failure mode of a split rule is a category that falls between the
halves. CodeMirror **5** and not 6 is a real tradeoff, recorded in
[ADR 0010](docs/adr/0010-codemirror-5-over-6.md): a maintenance-mode dependency,
accepted to keep an npm toolchain out of a Python project for one widget.

### Why localhost is not automatically safe

The server runs `git` and `pytest` on request, so it has two and a half guards on
it. It **binds to loopback only**, with the check inside the argument to
`uvicorn.run` so it cannot be dropped while rebasing. It **refuses any mutating
request that cannot prove it came from its own page** — because binding to
localhost does nothing to stop a malicious site in your browser from POSTing to
`http://127.0.0.1:8765`; a request carrying neither `Origin` nor `Sec-Fetch-Site`
is refused too, rather than waved through as "probably not a browser".

The half is a **`Host` allowlist**, and it is there because the first two do not
cover DNS rebinding. If `evil.example` resolves to `127.0.0.1`, the browser sends
`Origin: http://evil.example` to a request whose own `Host` is `evil.example` —
they *agree* — and reports `Sec-Fetch-Site: same-origin`, truthfully. Both guards
pass. Only the hostname gives it away, which is also why that check covers reads:
a rebound page that can read the HTML can read an attempt's transcript out of it.

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
a required check fails, and 2 when the attempt could not be run at all.

`solve` does the whole thing in one invocation, which is the right shape for one
answer at a time and is how CI grades every reference solution in the library. To
spread an attempt over several commands, see **Working on an attempt** below.

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

There is still no interactive console: a `.cmds` file is not a REPL, and the
console belongs in the web workbench, which is Phase 8. The workbench page already
exists and says so, with the two commands that drive the same attempt from a
terminal — what is missing is the console, the repo state panel and the commit
graph, not the attempt underneath them.

## Working on an attempt

An attempt outlives the process that started it, so it can be opened, worked on
and graded by different invocations:

```bash
uv run practice start git/revert-a-pushed-commit
uv run practice resume <id> --commands look-around.cmds
uv run practice resume <id> --commands the-fix.cmds
uv run practice submit <id>
```

Four processes, one repository, one event log and one budget — ten commands
yesterday and five today is fifteen of twenty-five. The budget belongs to the
attempt, not the invocation, which is what makes this a resumption rather than a
second go.

```bash
uv run practice attempts
uv run practice attempts --exercise git/revert-a-pushed-commit
uv run practice abandon <id>
```

`attempts` lists what is still open, oldest first, and says of each whether it
**can** be resumed — one whose workspace has been collected cannot, and the only
thing left is to abandon it. That listing plus `resume` and `abandon` is the
resume-or-abandon rule of [PLAN.md §8.1](docs/PLAN.md) in the form a terminal can
have it: an interrupted session is neither silently lost nor silently
resurrected. An interactive prompt on startup would be the literal reading and
the wrong one — it would block `practice solve` in CI.

Abandoning deletes the workspace and keeps the attempt, marked, with its whole
log. It is also the only way out of an exercise that was renamed or deleted from
the library while an attempt at it was open: that attempt can never be graded, so
`resume` refuses it and `abandon` does not.

Attempts and review cards live in one SQLite file under the user *data*
directory, not the cache — a workspace is rebuildable from a fixture and a
history is not ([ADR 0006](docs/adr/0006-sqlite-without-an-orm.md)). The schema
is hand-written SQL in numbered migration files, applied on first use; the
mappers are hand-written in both directions, and the round trip is unit-tested
against a plain dict with no database in the test.

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

Reports the attempt workspaces left on disk, and with `--no-dry-run` collects the
orphans. An orphan is defined precisely: *a workspace directory with no
corresponding `active` attempt row* — which is a question that could not be asked
before the attempt table existed, and is why this command spent three phases
reporting and never deleting.

The rule is decided on the directory name, which is the attempt's short id. That
matters: the leftover most worth collecting is an interrupted provision whose
metadata was never written, and a rule that joined on metadata could neither
explain it nor collect it. A workspace that *is* in use is never deleted, with or
without the flag, and there is no force option — the way to get rid of one is
`practice abandon`.

## Layout

```
src/practice/
├── domain/        pure data and functions; zero I/O
│   └── checks/    the 22 assertions, as pure functions over a read-only port
├── application/   use cases over ports, and the exercise-kind registry
├── adapters/
│   ├── sandbox/     builds a repository and runs commands in it
│   ├── git/         reads one back: GitRepoQuery, ScenarioGrader
│   ├── kata/        the pytest runner and its grader
│   ├── content/     the exercise library on disk
│   └── persistence/ in-memory stores, and sqlite/ behind the same ports
├── interface/
│   ├── web/         FastAPI + Jinja2 + HTMX; routes, templates, vendored assets
│   └── cli/         Typer: the second driving adapter over the same use cases
├── composition.py the single wiring point; the only cross-layer import
└── config.py      where the library, the workspaces and the database live
content/           exercises as declarative data — adding one needs no code
└── fixtures.lock  commit hashes every fixture must reproduce, on any platform
tools/             the one module that opens a socket, deliberately outside the wheel
docs/adr/          architecture decision records
tests/             unit · integration · content · web · e2e
```

`tools/vendor_assets.py` downloads the pinned assets and is **not** part of the
package: the wheel is built from `src/practice` alone, so nothing a user installs
can reach the internet even by accident. That is the offline claim expressed in
the build rather than in prose.

Dependencies point inward, and `tests/unit/test_architecture.py` fails the build
if that is ever violated — architecture that isn't tested decays. The same suite
enforces two narrower rules: only `adapters/sandbox` may import `subprocess`, and
only `adapters/persistence` may import `sqlite3`. The trust split the sandbox
rests on — **fixtures are trusted code, user commands are untrusted input** — is
only a split if there is exactly one place that starts a process; and the schema,
the migrations, the transaction boundary and the mapping are only behind the
repository ports if there is exactly one place that speaks SQL. Each rule is
paired with a test that the package really does import the module, so neither can
pass by there being no code at all.

The assertion functions are in `domain/checks/` rather than under `adapters/`
for the same kind of reason. They are pure functions over a `RepoQuery` port and
never shell out, so putting them inside the layer the coverage gate and the
architecture test police makes "testable with no git installed" a structural
fact rather than a happy accident. All 22 are unit-tested against an in-memory
fake in milliseconds; a conformance suite then proves that fake answers the same
questions real git does, which is the only thing that makes the fast tests
evidence about anything.
