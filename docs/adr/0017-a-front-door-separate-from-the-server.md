# 0017 — A front door (`practice up`) separate from the server (`practice serve`)

- **Status:** accepted
- **Date:** 2026-10-03
- **Phase:** Phase 12 — Polish and portfolio artifacts

## Context

Phase 12's exit criterion is that **a stranger can clone this, run one command,
and be practising in under two minutes** (PLAN.md §11). `practice serve` was the
closest thing to that command and it could not meet it, for a reason that is a
design property rather than an oversight.

Everything the app needs is discovered lazily, and every one of those choices is
right for the long run:

- `find_git` resolves git per command, against the ambient `PATH`.
- `Database` opens nothing until something is read or written, and migrates on
  first use. This is load-bearing: `composition.py` builds the whole object
  graph for `practice validate`, which never touches storage, and
  `test_building_the_graph_writes_nothing_to_disk` fails if wiring creates a
  file.
- `FilesystemContentRepository` reads the library when a page first asks for a
  list.

Each is correct and each surfaces a missing prerequisite **inside an HTTP
request**. On a fresh machine that means: the browser shows a stack trace, the
terminal shows a traceback from a threadpool, and neither says *install git*. It
arrives twenty minutes after installation, on the first exercise the solver
opens, having already done the work.

`serve`'s own contract makes it the wrong place to fix this. Its docstring says
"Run the web app on loopback, and nothing else", and
`test_building_the_app_reads_no_database` pins that claim: starting the server
must not create a database on a fresh machine. That property is what makes
`serve` the command CI and the test suite boot.

## Decision

**`practice up` is the front door. `practice serve` stays the plumbing.**

`up` runs four checks before binding anything, creates what it can, and then
hands the same object graph to the same `uvicorn.run`:

| step | asks | creates |
|---|---|---|
| `git` | can `git` be resolved on `PATH`? | — |
| `library` | does the content root list exercises? | — |
| `workspaces` | can the cache directory be created? | the directory |
| `database` | can every migration be applied? | the file, migrated |

Then it prints where all four live, says once if this run created the attempt
history, opens the browser and serves. `--no-open` skips the browser.

Three sub-decisions are deliberate:

- **It refuses rather than serving degraded.** Every step is a prerequisite with
  no fallback behind it, so a blocked step is exit 2 — matching every other
  "this invocation cannot be satisfied" in the CLI.
- **Every step runs, and all the problems are reported together.** A chain that
  stopped at the first failure would make a stranger run this three times to
  learn three facts, and a machine with no git plausibly has no writable data
  directory either.
- **The loopback guard runs first**, through a `_bound` shared with `serve`, so
  §8.3's rule has one implementation and one test — and so a refused `--host`
  never migrates a database on behalf of an invocation it was not going to
  honour.

## Consequences

**What it buys.** The exit criterion is met and testable:
`test_a_clean_machine_is_set_up_in_one_command` starts with no database and no
workspace root and ends with a migrated file, a created directory, a browser
pointed at the app and a server running. `serve` keeps its contract and its
test, so CI and the test suite boot a command that still touches nothing. And a
`MigrationError` — a schema written by a newer `practice` than this one — is now
a sentence before anything is at stake rather than a 500 over an attempt the
solver has already finished.

**What it costs.**

- **Two commands that both start a server**, and a user has to know which. The
  README says `up` and mentions `serve` once, which is the whole mitigation.
- **A refusing run still leaves state.** The workspace directory and the
  database file are created even when git is missing, because every step runs.
  Both are empty, both are where the first attempt would have created them
  anyway, and `test_prepare_creates_nothing_it_was_not_asked_to` bounds it — but
  it is a side effect on a command that then exits 2.
- **One connection per launch, forever.** `migrate()` is idempotent, so after
  the first run this is a connection and a one-row read that buys nothing. That
  is the price of the first run being safe.
- **The browser races the server.** `uvicorn.run` blocks, so there is no "after"
  to open the tab in; it is opened just before. Sometimes the tab wins and the
  solver reloads.
- **`up` is not covered by the architecture test's strongest rules.**
  `open_in_browser` reaches a process through `webbrowser`, which
  `test_only_the_sandbox_starts_a_process` does not see, because it looks for
  `subprocess` and `signal`. It is in `adapters/sandbox` anyway, next to
  `editor.py`, by the same argument that module's docstring makes — but it is
  there by choice and not by enforcement, which is worth knowing.

## Alternatives considered

**Fold the setup into `serve`, with `--no-open`.** One command, no new surface,
and the closest to winning. Rejected because of what it costs `serve`:
`test_building_the_app_reads_no_database` would have to go, and with it the
claim that booting the server is free of side effects — which is exactly why
every web test and CI job can boot it. The alternative would be a `--setup/
--no-setup` flag, at which point there are two commands again, spelled worse.

**`up` plus a separate `practice doctor` that reports without serving.**
Tempting, and it is what a larger tool would have. Rejected under §13's rule
that an abstraction must earn its keep: `doctor` would print exactly what `up`
prints, for the one case where somebody wants the report and not the server, and
nothing in the project has wanted that yet. `up --no-open` and Ctrl-C covers it.

**Refuse nothing, and show the problems on the dashboard.** Serve anyway, and
render a warning banner in the web UI. Genuinely better for discoverability if
the solver is already in the browser — and rejected because the first failure
mode is a machine with no git, where every exercise is unopenable and a banner
is a worse version of an exit code. The terminal is where the fix gets typed.

**Check git by running `git --version`.** More thorough: it would catch a git
that resolves but cannot execute, and report the version. Rejected twice over —
it would start a process outside `adapters/sandbox`, which is the one rule this
project is strictest about, and this project has no documented version floor to
check against. Resolution is what fails on a fresh machine.

**Run `validate_library` as the library check.** It is the thorough audit and it
would catch a malformed exercise precisely. Rejected on cost: it walks all 54
exercises on every launch, and the question `up` needs answered is "is there a
library here at all". A `ContentError` is still caught — the repository fails the
*whole* listing on one bad file, so one bad exercise is a browse page that 500s,
not a smaller library — and the message it prints is "run `practice validate`".

## Revisit if

- **A second thing ever wants the preflight without the server** — a `doctor`, a
  CI smoke check, a packaged installer. Then `prepare` is already the seam and
  the second command earns its keep.
- **A prerequisite appears that `up` should warn about rather than refuse over.**
  Today all four are hard blockers. The first soft one changes `Step` from
  ok/problem to three states, and that is the moment to ask whether the
  dashboard banner was right after all.
- **`serve` is ever deleted or merged away.** This ADR rests on `serve` having a
  contract worth protecting; if the test suite stops booting it, the reason for
  two commands goes with it.
