# 0013 — Grade-on-save is a preview that persists nothing

- **Status:** accepted
- **Date:** 2026-10-02
- **Phase:** Phase 10 — Own-editor mode

## Context

Own-editor mode gives the solver the real file a kata is graded from and
re-grades it every time they save, streaming the verdict back to the browser
(PLAN.md §11, Phase 10). The obvious way to build that is to call the use case
that already exists — `SubmitSolution` — on every save. It cannot work, and the
reason is a rule rather than a bug.

Three things are true at once and they do not fit together:

1. **Submission ends an attempt.** `Attempt.complete` sets the status and
   refuses a second call (§4.3), and `SubmitSolution` disposes of the workspace
   on success (§8.1 ties workspace lifetime to `ACTIVE`). So the first Ctrl+S
   would finish the exercise, delete the directory holding the file being
   edited, and the second would be told the attempt is completed.

2. **The event log is a record of what the solver did in the exercise**, and
   Phase 8 decided explicitly that an editor save is *not* one of those things
   (PLAN.md §16): it is a keystroke. Three things read that log — the §6.3
   process assertions, the Phase 9 grade suggestion, and
   `kata.grader.latest_source` — and all three are built on the log containing
   deliberate acts.

3. **`Grader.grade` takes an `Attempt`, not a source string**, on purpose: a
   verdict is derived from something the attempt remembers, so it is replayable
   and never about code nobody submitted. A grader handed a bare string could
   produce a verdict for anything.

A save has to produce a verdict without ending the attempt (1), without
appending to the log (2), and without weakening the grader's contract (3).

## Decision

**A save produces a `Draft`, not a `Submission`, and nothing is written.**

`WatchSolutionFile` loads the attempt fresh on every save, hands it the file's
contents **in memory**, grades that aggregate, and throws it away:

```python
attempt = self.attempts.get(attempt_id)   # a fresh aggregate from the store
attempt.save_solution(source, at=now)     # in memory only
verdict = grader.grade(exercise, workspace, attempt)
# and it is never saved
```

The `SolutionSaved` event exists for the length of one grading pass, which is
exactly as long as the grader's contract needs it to. The stored log is
untouched, the attempt stays `ACTIVE`, and the workspace survives. Submitting
remains something the solver does on purpose, with a button, and is the only
thing that writes.

Two consequences are deliberate rather than incidental:

- **The attempt is re-read on every save**, so an attempt submitted from another
  tab ends the stream — through `Attempt.save_solution` refusing, whose sentence
  is already the right one.
- **The browser editor mirrors the file and goes read-only.** With two editors on
  one attempt there has to be one source of truth, and it is the file. The
  stream carries the source alongside the verdict, which also fixes what Submit
  means in this mode: *it sends the source the verdict on screen was computed
  from.*

## Consequences

**What it buys.** Grade-on-save is safe to drive from a file watcher, because it
is a read: any number of saves, no state change, nothing to undo. The log stays
a record of deliberate acts, so the grade suggestion and the process assertions
need no new rule about which `SolutionSaved` events to ignore. And a preview and
a submission describe one solution identically — both run the same grader and
render `partials/verdict.html` — so a solver is never shown one verdict and then
given a different one.

**What it costs.**

- **A draft is not recoverable.** If the browser is closed, the only record of
  what was graded is the file itself. That is the right trade for an editor
  save, and it is the same trade the browser editor already makes.
- **A preview of a kata with a complexity expectation can never be a clean
  `PASS`.** Declaring the cost is part of submitting, so every draft carries the
  *not declared* advisory. Accurate, and a standing reminder, but it does mean
  the outcome word changes at submission time for a solver who does declare.
- **Grading now has a concurrency problem it did not have.** Two tabs on one
  attempt are two streams, and two passes over one workspace overwrite each
  other's `solution.py` and `report.json`. Submission could never collide with
  itself, so this is new. Answered by serialising the write-run-read sequence
  inside `PytestKataRunner`, which is the thing that owns those files.
- **The event log no longer shows the work in progress.** A future "where did I
  go wrong" view will find one source per attempt rather than forty snapshots.
  If that view is wanted, the honest way to get it is a deliberate autosave the
  solver can see, not a side effect of a watcher.

## Alternatives considered

**Append a `SolutionSaved` event per save and grade from the log.** The closest
to winning, because it needs no new use case: `SubmitSolution` minus the
`complete` call. Rejected because it makes the log a transcript of keystrokes.
`latest_source` would mean "whatever was last saved" rather than "what was
submitted"; the Phase 9 grade suggestion reads the log to tell *passed* from
*passed with three hints*, and would have to learn to skip a kind of entry; and
every §6.3 process assertion would acquire the same exception. PLAN.md §16
already settled the principle for the browser editor — this is the same
question with a file watcher attached, and answering it differently would have
made the rule depend on which editor you used.

**Auto-submit on save.** Rejected outright: it finishes the attempt on the first
Ctrl+S, deletes the workspace the solver is editing in, and makes an accidental
save an irreversible act. It also destroys the thing spaced repetition measures
— an attempt would be graded on the first thing that compiled rather than on
the answer.

**Grade in a throwaway copy of the workspace.** Would have fixed the
concurrency problem too, by giving each pass its own directory. Rejected on
cost: provisioning is the expensive part of an attempt (a fixture run, a git
repository, a copied test suite), and paying it on every Ctrl+S to avoid one
lock is the wrong trade. It also breaks the thing that makes the preview worth
trusting — it would grade a *copy* of the file, so a verdict could be about a
directory the solver cannot inspect.

**Let the browser poll a grading endpoint.** No watcher, no stream, no port: a
timer and the existing fragment machinery. Rejected because the question it
answers is worse. Polling grades code that has not changed, which starts a
pytest subprocess for nothing, and the interval is either slow enough to feel
broken or fast enough to keep a core busy. A save is an event and the operating
system already reports it.

**Make `SubmitSolution` take `source=None` and read the file.** This is a real
alternative to a *separate* use case, and it is about submission rather than
preview, but it was considered here because it would let the file-mode Submit
button send nothing. Rejected because the stream already carries the source to
the browser, so the existing route works unchanged — and a `None` that means
"look on disk" puts filesystem knowledge into the use case that closes
attempts.

## Revisit if

- A "show me my attempt as it developed" view is actually wanted. Then the
  decision to persist nothing is what blocks it, and the replacement is an
  explicit autosave — a thing the solver can see and the log can name — rather
  than reinterpreting a watcher's events as intent.
- Grading becomes expensive enough that re-running it on every save is wasteful
  (a kata whose suite takes seconds, or a language with a compile step). Then
  the preview needs debouncing or an explicit "grade now" control, and the
  question of what a save *means* is open again.
- A second grading pass ever needs to run concurrently with a submission for a
  reason other than a second tab. The lock in `PytestKataRunner` is sized for
  one process; a second server, or a CLI watching the same workspace, would need
  a lock the filesystem can see.
