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

**Status: v1.0.0, plus three stretch items.** All twelve planned phases are done —
**62 exercises: 24 git scenarios, 30 katas and 8 SQL drills, every one of them
graded.** The core bet works, a session survives the terminal it was opened in,
every exercise kind is solved in a browser *or in your own editor*, and the tool
answers *what should I practise today?* instead of leaving it to you.

Phases 13, 14 and 15 are post-v1, taken from a menu by appetite, and all three
were chosen for the same reason: they were the items with a **prediction**
attached. **FSRS behind the same `Scheduler` port as SM-2**, and the prediction
held ([ADR 0018](docs/adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)).
Then **SQL drills as a third exercise kind** — seed a database, write the SQL,
and get graded on the rows you returned *and the state you left the database in*
— where the prediction was half right, which was the more useful outcome
([ADR 0019](docs/adr/0019-sql-drills-as-a-third-exercise-kind.md)). Then
**interview mode**, where the prediction was in the menu entry itself and one of
its three clauses turned out not to be buildable at all
([ADR 0020](docs/adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md)).
A git scenario is graded on what your commands actually did, from a console or
from the terminal:

![A terminal replaying `practice solve git/revert-a-pushed-commit`: three commands run, the content check passes, and the history check fails.](docs/demo.svg)

That is the whole argument in one verdict. The **content check passes** — the
files are byte-identical to what a correct `git revert` produces — and the
ancestry check is what tells the two apart. A tool grading on file content
accepts this answer; a tool matching command text would have to guess which of
two dozen correct phrasings to allow.

The demo is not a recording. `docs/demo/session.txt` is the captured output of
that command and `docs/demo/render.py` draws it, so the transcript above is
regenerated rather than redrawn — and you can select the text in it
([ADR 0016](docs/adr/0016-a-generated-demo-not-a-recorded-one.md)).

Underneath it: 20 pure assertion functions over a read-only port, implemented
twice (real git, in-memory fake) and proved to agree by a conformance suite, and
a content suite that grades every reference solution in the library and holds
every counter-example to exactly the checks it declares.

**Nothing in `content/` is borrowed.** Every prompt, hint, note, hidden test and
reference solution is written for this repository
([ADR 0009](docs/adr/0009-ship-our-own-prompts.md)) — which is what lets a prompt
state exactly what the grader checks, and what makes the notes the product rather
than a restatement of someone else's problem statement.

See [docs/PLAN.md](docs/PLAN.md) for the full design and the phase plan, and
[docs/adr/](docs/adr/) for the twenty decisions and the alternatives that were
rejected — the rejected half is usually the half worth reading.
[docs/postmortem.md](docs/postmortem.md) is the honest version: what the bet
bought, six things that would be done differently, and five that are still
wrong.

## Getting started

Requires [uv](https://docs.astral.sh/uv/), Python 3.13 and git. Nothing else — no
npm, no bundler, no network.

```bash
uv sync
uv run practice up
```

`up` is the front door. It resolves git, counts the library, creates the
workspace directory, migrates the database, names the scheduler, and then opens
your browser on `http://127.0.0.1:8765`:

```
  ok   git         /usr/bin/git
  ok   library     62 exercises (24 git scenarios, 30 katas, 8 SQL drills) in ~/swe-practice/content
  ok   workspaces  ~/.cache/swe-practice/ws
  ok   database    ~/.local/share/swe-practice/practice.db (created v2)
  ok   scheduler   sm2 (Sm2Scheduler())

First run: your attempt history now lives at ~/.local/share/swe-practice/practice.db.

http://127.0.0.1:8765
```

It **refuses** rather than serving degraded, and it reports every problem in one
pass rather than one per run: with no git there is no fixture, with no library
there is nothing to offer, with no database an attempt cannot be saved. A server
that booted anyway would be a tool that looks fine right up until the moment you
have done the work
([ADR 0017](docs/adr/0017-a-front-door-separate-from-the-server.md)).

From there: see what is due, start an attempt, write a solution in the editor or
type real git into a console, read the verdict, and schedule the next sighting.
Everything it serves comes off the disk, so it works with the wifi off.
`practice serve` is the same server *without* the setup — that is what CI and the
test suite boot — and `practice up --no-open` is for a box with no browser on it.

The terminal is a second adapter over the same use cases, documented below. It is
not a fallback — it is the proof that the core is not secretly coupled to HTTP.

## Checks

The same four commands CI runs, on Linux and Windows:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-report=term-missing -n 4 --dist loadfile
```

Test selection follows the directory layout under `tests/` — markers are applied
automatically, so `uv run pytest -m unit` gets the fast pure tests,
`-m integration` gets the ones that touch the filesystem, and `-m content` runs
the library checks over every exercise on disk.

**Four workers, not `-n auto`, and the number is measured rather than chosen.**
Every worker spawns its own subprocesses — a bash fixture and a dozen `git`
invocations per scenario, a `pytest` per kata — so the useful worker count tracks
subprocess load rather than cores. On twelve cores, `-n auto` ran the suite in
3m42s, then 7m36s, then 8m41s, and one of those runs *failed* by taking a kata
past the ten-second wall-clock limit the suite grades against on purpose. `-n 4`
is 7m20s and repeatable, which is the property that matters in the tier that
decides. `--dist loadfile` keeps every test in a file on one worker, which is
what lets the content suite share its workspaces instead of rebuilding them.

## The web app

```bash
uv run practice up
```

`/` is the dashboard — what is due, your streak, your weakest tags.
`/browse` filters the library by kind, difficulty and tag, and starts an attempt;
`/attempt/{id}` is the workbench; `/progress` is the long form. For a kata that is the prompt beside a CodeMirror
editor seeded from the exercise's stub; for a git scenario it is a **command
console over the real repository**, with a repo state panel and a commit graph
beside it. An attempt already open shows **Resume** instead of **Start**, because a
second one would split one piece of work across two budgets.

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

### The scenario workbench

Type `git revert --no-edit HEAD` into the console and three things come back in one
response: the command's output appended to the transcript, the command budget, and
the whole repo state panel — HEAD and whether it is detached, the local branches,
what `origin/main` points at, the four worktree states, the stash, and a
hand-rolled SVG commit graph. htmx swaps the first in place and the rest by id, so
there is no client-side model of a repository anywhere.

The thing to watch is `git reset --hard HEAD~1`. `main` moves down a commit, the
commit it left behind stays on the graph because `origin/main` still points at it,
and the two lines of the panel say what you just did to your teammate before the
verdict does.

**The panel reads the repository through the same port the grader does**
([ADR 0012](docs/adr/0012-inspect-the-repository-through-the-grading-port.md)). A
display-only git wrapper would have been less code and would have let the panel and
the verdict quietly disagree — `worktree_clean` ignores untracked files by design,
so a panel built on raw `git status` reads as dirty where the grader reads as
clean, and nothing tells you which one to believe.

Hints are revealed one at a time, and each reveal is recorded on the attempt
alongside the commands — because "passed, with three of four hints" is a different
outcome from "passed", and that is the record the spaced-repetition model reads.

### Your own editor

A textarea is not where anyone wants to write a hash map. **Open in my editor**
starts your editor on the file the kata is actually graded from, and from then on
the browser re-grades it every time you press Ctrl+S:

```
YOUR EDITOR
The solution for this attempt is a real file. Edit and save it in whatever you
like:

  C:\Users\you\AppData\Local\swe-practice\ws\18ec95b0\repo\stub.py

Opened in your editor. Watching for saves. Re-graded every time you save.
```

There was nothing to scaffold, which is the nice part: the provisioner has
copied the stub into the workspace since Phase 3, and the browser editor already
reads it from there — so the stub *is* the working copy and all that was missing
was its path. `practice start` prints it too, which means the terminal has had
own-editor mode all along:

```bash
uv run practice start katas/two-sum
# Edit .../ws/18ec95b0/repo/stub.py in your own editor, then grade it with
# `practice submit 18ec95b0-... --source .../ws/18ec95b0/repo/stub.py`.
```

Which editor is one environment variable, `PRACTICE_EDITOR`, defaulting to
`code`. `$EDITOR` is deliberately *not* consulted: it names a program that
expects to own a terminal, and this launch has none — `EDITOR=vim` would start
successfully, draw nothing anywhere, and report success. If the editor cannot be
started the panel says so **and still shows the path**, because the feature is
the file and the launch is the convenience on top of it.

**A save is a preview, never a submission**
([ADR 0013](docs/adr/0013-grade-on-save-is-a-preview.md)). Grading on save by
calling the submit path cannot work — submission completes the attempt and
deletes the workspace holding the file you are editing — and recording each save
in the event log would be worse: the log is a record of what you *did in the
exercise*, and three things read it that way. So a save loads the attempt, hands
it the file's contents in memory, grades that, and throws it away. Submitting is
still a button, and it is still the only thing that writes.

The verdict arrives over **server-sent events**, framed by hand with native
`EventSource` rather than htmx's SSE extension — which htmx 2 ships separately,
and which would have been a fifth hash-pinned vendored file for one panel. What
crosses the wire is the same `partials/verdict.html` fragment a submission
returns, plus the file's own text, so the browser editor goes read-only and
mirrors what is on disk. That is what makes Submit unambiguous with two editors
open: it sends the source the verdict on screen was computed from.

## Sitting one under interview conditions

Every exercise can be opened a second way, and the choice is made once:

```bash
uv run practice start katas/two-sum --interview
#   ok   attempt 35ee1ef4-fee3-4ea1-9638-e330757dc01b
#          started 2026-10-04T18:10:57+00:00, 0 events, no hints, 15 minute limit
#
# Write your answer in a file of your own, then grade it with
# `practice submit 35ee1ef4-... --source FILE`.
```

Three things change: **the hints are withheld**, **a clock starts** at the
author's own estimate, and **the path to the workspace is not printed** — nor is
"Open in my editor" drawn in the browser. The mode is a field on the attempt's
stored policy, so `resume` and `submit` apply it without being told, and it
cannot be renegotiated halfway through.

Two of those cost almost nothing, which is the interesting part. Withholding the
hints needed **no new code path at all**: the policy is built with an empty hint
list, which is a state the aggregate already refused to hand a hint out of and
the workbench already declined to draw a panel for. And the clock needed no new
grading rule, because the schedule control has compared your time against
`estimated_minutes` since Phase 9 — an interview's deadline *is*
`estimated_minutes`, so a timed attempt was already graded from its end state.

**The third one is not what the plan said it would be, and this is the honest
version.** The menu entry said *"no test peeking"*. That is not implementable: a
kata's hidden suite has to be in the workspace for `pytest` to run it, the
workspace is a directory on your own machine, and this project settled in Phase 3
that you own the machine — the sandbox is a blast-radius boundary, not a security
one. So what interview mode actually does is **withdraw every affordance the tool
provides for peeking**, and say so. The predicate in the code is called
`reveals_workspace`, not `hides_tests`. If you go looking for the cache
directory, the tests are there.
[ADR 0020](docs/adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md)
spends its longest section on the stronger version — move the suite out of the
workspace and point `pytest` at it elsewhere — and rejects it for widening a port
to buy a boundary that still would not be one.

**Running over the clock does not refuse the submission.** Grading the end state
is the whole bet; a gate that threw away a working answer for being four minutes
late would be enforcing a rule the verdict can simply read. And the clock in the
browser is rendered when the page loads, with *"as of this page load"* next to
it, rather than ticking — a countdown that ran to zero and changed nothing would
be the one number on the page that nothing grades.

## What to practise today

Under the verdict is a schedule control, and it is the thing that turns a pile of
graded attempts into a training system. The tool **suggests** the grade, because
it has three readings you do not: the verdict it derived from the end state, the
hints you revealed, and the time against the author's own estimate. A clean pass
inside the estimate with no hints is `easy`; each of the three costs a step; a
failure is `again`, and a *pass* never is — passing messily is not the same as
not knowing it.

```
SCHEDULE
Suggested: good — passed, but 1 hint revealed
  [ again ]  [ hard ]  [ good ★ ]  [ easy ]
```

Nothing is scheduled until a button is pressed, which is deliberate: a card is
replaced rather than versioned, so applying the suggestion automatically would
make an override impossible to honour. One attempt moves a card once — a
double-click is refused, because advancing the interval twice for one piece of
evidence is not undoable.

The scheduler is SM-2 by default, the four-grade Anki variant, as a pure function
with no clock and no repository — forty lines held by hypothesis over thousands of
generated cards, including the `max(previous + 1, ...)` interval clamp without
which "consecutive *good* strictly increases the interval" is false at the ease
floor.

**FSRS is the second implementation, and `PRACTICE_SCHEDULER=fsrs` is the whole
of switching to it.** Phase 9 deferred it and wrote down what the swap would cost
([ADR 0008](docs/adr/0008-sm2-first-with-fsrs-behind-a-port.md)): one line at the
composition root, and a migration that adds columns rather than reusing SM-2's.
Both halves held
([ADR 0018](docs/adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)) —
twelve files under `src/`, not one of them a use case, a grader or a route, with
the SQLite mapper and the review repository each gaining the two new column
names and nothing else touched. And a card SM-2 left at fifteen days is
*adopted* by FSRS rather than reset, because at 90% retention an FSRS interval is
exactly its stability.

Three things came out of writing the second one that could not have come out of
writing the first.

- **One of the four properties the plan calls the scheduler's turns out to be
  SM-2's.** "*`again` always resets to one day or less*" is a policy, not a law:
  FSRS schedules a lapse from its own post-lapse stability, which on an
  established card is weeks. The other three, and the weaker *a lapse never
  lengthens an established interval*, are now a conformance suite run against
  both.
- **The interval clamp is not an SM-2 artefact.** FSRS stalls too — its stability
  growth term is exactly zero when no days have passed, so grading a card twice
  in one day returns the stability it was given. Two unrelated causes, one fix:
  the clamp belongs to whole-day intervals.
- **One number on this page was meaningless under FSRS.** The panel printed the
  ease factor unconditionally, which FSRS never moves. Present, correctly
  formatted, and wrong — so no fragment assertion was ever going to fail on it.
  Found by switching the scheduler and looking.

SM-2 stays the default, and the reason is the honest one: FSRS's advantage comes
from parameters fitted to a log of your own reviews, this tool keeps one row per
exercise and no log, and FSRS on unfitted defaults is FSRS without the thing that
makes it better.

`/` then answers the question. Everything due comes first, longest-overdue first,
followed by everything that has never been scheduled — which on a fresh install
is the whole library, and is the state where the question most needs an answer. A
queue built from the card table alone would say "nothing due" beside an untouched
library.

`/progress` is the long form: pass rate and lapses per **tag** rather than per
exercise, because "you failed `git/recover-a-lost-commit`" is something you
already knew and tags are what generalise; an activity window that draws its idle
days, because a month with seven scattered attempts and a week with seven
consecutive ones are opposite facts about a habit; and the whole attempt history.
Both charts are **hand-rolled inline SVG generated in Python** — no chart
library, no dependency, every colour a CSS custom property so the drawings follow
the light scheme, and every figure printed in words beside the picture, because a
chart is the fastest way to see a shape and the worst way to learn a number.

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

A `.cmds` file is not a REPL, and it was never meant to be one: the interactive
console is in the web workbench, where a commit graph can actually be drawn. Both
drive the same attempt, the same log and the same budget, so a session started in
the browser can be finished from a terminal and the console shows the commands the
terminal ran.

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

Reports every problem in all 62 exercises in one pass, located to the field, and
exits non-zero if anything is wrong — so CI depends on it. It runs nothing, so
it works on a machine with no git, and it prints what a passing run does **not**
prove.

It also audits `content/curriculum.yaml`, the hand-written manifest that decides
what order the library is offered in
([ADR 0014](docs/adr/0014-a-hand-ordered-curriculum-manifest.md)). It has to name
every exercise exactly once and nothing that is not on disk, so an exercise added
without a line in it fails here rather than quietly appearing at the end of the
list.

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

## Architecture

![Dependencies point inward: the CLI and the web app call the application layer, the application layer and the domain sit at the centre, and the adapters implement the domain's ports.](docs/architecture.svg)

Ports and adapters, with the boundary enforced by a test rather than by a
convention ([ADR 0002](docs/adr/0002-ports-and-adapters-with-an-enforced-boundary.md)).
Two rules shape what gets added to it:

- **A port needs two or more real or test implementations, or it gets deleted.**
  A protocol nothing has had to satisfy has not been shown to work. The rule has
  been applied in anger rather than quoted: Phase 11 deleted two assertions and
  a port method after 24 git scenarios wanted none of them.
- **Deliberate duplication is a pattern here, not a smell.** The aggregate
  refuses to *reach* an impossible state, the schema refuses to *store* one, and
  the adapter refuses to *execute* a disallowed command. Three layers, three
  different jobs, and each one says in its docstring which job it is doing.

## Layout

```
src/practice/
├── domain/        pure data and functions; zero I/O
│   ├── checks/      the 20 git assertions, pure over a read-only port
│   ├── drills/      the 10 SQL assertions, pure over a second read-only port
│   └── scheduling/  SM-2 and FSRS behind one port, and the grade read off an attempt
├── application/   use cases over ports, the kind registry, graph layout, progress
├── adapters/
│   ├── sandbox/     builds a repository, runs commands in it, opens your editor
│   ├── git/         reads one back: GitRepoQuery, ScenarioGrader
│   ├── kata/        the pytest runner and its grader
│   ├── sql/         seeds a database in memory, runs one answer, grades the result
│   ├── content/     the exercise library on disk
│   └── persistence/ in-memory stores, and sqlite/ behind the same ports
├── interface/
│   ├── web/         FastAPI + Jinja2 + HTMX; routes, templates, three SVG charts
│   └── cli/         Typer: the second driving adapter, plus the first-run launcher
├── composition.py the single wiring point; the only cross-layer import
└── config.py      where the library, the workspaces and the database live
content/           62 exercises as declarative data — adding one needs no code
├── curriculum.yaml eleven tracks in order; validate holds it to covering them all
└── fixtures.lock  commit hashes every fixture must reproduce, on any platform
tools/             the one module that opens a socket, deliberately outside the wheel
docs/adr/          architecture decision records
docs/demo/         the captured session, and the script that draws docs/demo.svg
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
fact rather than a happy accident. All 20 are unit-tested against an in-memory
fake in milliseconds; a conformance suite then proves that fake answers the same
questions real git does, which is the only thing that makes the fast tests
evidence about anything.
