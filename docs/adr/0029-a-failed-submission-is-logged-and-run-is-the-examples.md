# 0029 — A failed submission is logged rather than final, and Run is the examples rather than the suite

- **Status:** accepted
- **Date:** 2026-10-16
- **Phase:** after Phase 21 (a request from using the tool)

## Context

The request was two things, both named after LeetCode and NeetCode: *let me
try a solution before submitting it*, and *don't make a failed submission the
end -- "cannot submit: attempt 4fcff95d is completed" -- just log the fail and
let me go again.*

Four things were true going in.

**Every submission completed its attempt.** `SubmitSolution` and
`SubmitScenario` called `Attempt.complete` with whatever verdict came back, and
disposed of the workspace. So a wrong answer was a finished attempt, the next
press of Submit was refused by the aggregate, and the only way to try again was
the *Try this one again* button under the verdict, which starts a new attempt
from the stub -- throwing away the code, and for a scenario the repository the
solver had spent twenty commands building.

**ADR 0013 rested on that.** Grade-on-save had to be a preview *because*
"submission ends an attempt"; the first Ctrl+S would otherwise have finished
the exercise. Own-editor mode already grades against the hidden suite on every
save without recording anything -- a full-suite preview exists, for anyone who
opens their own editor.

**Three readers assume one verdict per attempt.** The progress summary counts
completed attempts and their verdicts; the grade suggestion reads one verdict,
the hint log and the elapsed time; `OfferReview` refuses an attempt with no
verdict. An attempt that stayed open until it passed, with abandoning as the
only other exit, would vanish from all three whenever somebody gave up.

**A kata's examples are runnable source** (ADR 0027), executed against every
reference by the content suite and printed on their own tab. What they had
never been is run against the *solver's* code.

## Decision

**A failing verdict is appended to the attempt's log as a `SubmissionFailed`
event, carrying the verdict, and the attempt stays open.** Only a pass
completes it. The rule is `Attempt.submit`, which both submit use cases call,
so neither restates it: it returns whether the attempt closed, and the
workspace is disposed only then. A fourth event kind needs migration 0005,
which rebuilds `attempt_events` because SQLite cannot alter a `CHECK`.

**`Attempt.concede` closes an open attempt on its most recent failed
verdict.** This is what keeps the three readers honest: a solver who stops
after failing records the fail they got, so progress counts it and the
schedule control offers `AGAIN`. It grades nothing, and is refused for an
attempt that has not failed -- grading a fresh verdict there would be a submit
button with another label. The workbench shows it under a failed verdict as
*Stop and record the fail*; the CLI has `practice concede`.

**Run executes the kata's examples against the editor's contents, and
records nothing.** Not the hidden suite: the examples the solver can already
read, each shown with what it should give, what came back -- or the
exception's last line -- and what it printed. A new port, `ExampleRunner`,
implemented by `KataExampleRunner` over a harness copied into the workspace
the way the pytest report plugin is, and by a recording double in the tests.
It shares the kata runner's lock, because both write `solution.py` into the
same directory. The CLI has `practice try`.

Three consequences follow from these and are part of the decision:

- **The grade suggestion gains a fourth penalty**: a pass after one or more
  failed submissions costs one step, however many there were.
- **The tutor context includes failed submissions**, verdict and all. Inside
  the spoiler boundary ADR 0023 draws, because the solver was shown each one
  when it failed; the attempt's own verdict and the author's notes stay
  withheld until it is over.
- **`practice solve` concedes a failure on the spot**, because it is one-shot
  -- it grades *an* answer, and an attempt left open behind every failing run,
  CI's included, would be a workspace nobody comes back for.

## Consequences

**What it buys.** The loop the request describes: run against the examples,
submit, read what failed, fix it in the same editor or the same repository,
submit again. Nothing is thrown away between tries, and every failure is in
the log in the order it happened, which is the "where did I go wrong" view
ADR 0013's *Revisit if* anticipated -- built from deliberate acts rather than
from keystrokes.

**What it costs.**

- **A failed verdict is now feedback mid-attempt, in interview mode too.**
  Its failing checks carry their explanations, and an interview withholds
  hints. A solver can submit something wrong to read what the checks want.
  Accepted, on the grounds an interview would accept it -- being told a case
  fails and fixing it is the work -- and because the suggestion's new penalty
  means it is not free. It is the one place this change pulls against ADR
  0020, and the place to look first if interview mode is tightened.
- **Pass rate on the progress page changes meaning.** It was first-try passes
  over attempts; now it is attempts that eventually passed. A tag where
  everything passed on the third try reads as 100%. The log holds what is
  needed to report first-try passes, and nothing reports it yet.
- **An attempt that is never conceded or abandoned stays open**, with its
  workspace, which is what the resume prompt and `practice gc` already handle
  for an attempt that was never submitted.
- **Run is a second subprocess path for solver code.** Under the same
  isolation as the hidden suite (`-I`, the scoped environment, the kata's time
  limit), and serialised behind the same lock -- so a Run pressed during a
  grading pass waits for it.
- **The harness restates the content suite's comparison.** `repr` of the plain
  form, with nodes walked by shape, written again in a file that cannot import
  the suite. Held together by running five shipped references, one per shape
  of answer, through the harness in `tests/integration/kata/test_examples.py`.

## Alternatives considered

**Keep completing on failure, and make *Try this one again* carry the code
forward.** The closest to winning, because it changes nothing about what an
attempt is: one verdict each, progress and the suggestion untouched. Rejected
because it answers the kata half of the request and not the scenario half. A
retry is a new attempt, a new attempt runs the fixture, and the repository the
solver was fixing is gone. Carrying a repository between attempts would be a
second provisioning path. It also makes the history read as five attempts
where the solver made one.

**Stay open on failure, with no concede.** Simpler by a use case and a button.
Rejected because the way out of a stuck attempt would be `abandon`, which
keeps no verdict: a solver who failed three times and gave up would leave no
trace on the progress page and nothing for the scheduler, which is exactly the
exercise spaced repetition most needs to bring back.

**Make abandoning a failed attempt record the fail.** Concede without a new
word. Rejected because it changes what an existing command means depending on
the log, and *abandon* is also the exit for an attempt whose exercise has left
the library, where there is nothing to record a fail against.

**Run grades the hidden suite without recording** -- `WatchSolutionFile`'s
preview, behind a button. Almost free to build. Rejected because it makes
Submit a formality: with failures no longer final, a full-suite run that
records nothing is a submission that cannot be counted, and the suite becomes
something to iterate against rather than something that checks. The split
LeetCode makes is the one the request asked for, and it is the visible cases
against the hidden ones.

**Run in-process, like the content suite runs examples against references.**
No subprocess, no harness file. Rejected outright: that path is safe because
the reference is trusted content, and the solver's source is not. Only
`adapters/sandbox` starts a process (`test_architecture.py`), and the solver's
code runs in one.

**A `run_examples` method on `Grader`.** No new port. Rejected for the reason
Phase 14 gave about `isinstance(spec, KataSpec)`: only a kata has examples, so
the scenario and drill graders would each implement a method whose only body
is a refusal.

## Revisit if

- Interview mode needs to mean *no feedback until you are done*. Then a failed
  submission under interview conditions should show the outcome and the count
  and withhold the explanations -- or an interview should keep one submission.
- First-try pass rate is wanted on the progress page. The failed submissions
  are in the log; it is a question for `summarise`, not for the schema.
- A SQL drill wants a Run button. It has no examples, so the honest version is
  *show me my rows* against the seed -- a second `ExampleRunner` with a
  different result shape, which would test whether `Trial` is the right one.
