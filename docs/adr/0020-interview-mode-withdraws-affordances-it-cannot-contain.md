# 0020 — Interview mode is a stored policy that withdraws affordances, not a containment boundary

- **Status:** accepted
- **Date:** 2026-10-04
- **Phase:** Phase 15

## Context

PLAN.md §11's Phase 13 menu lists *"interview mode (timed, no hints, no test
peeking)"* and puts one thing in its **Touches** column: *application-layer
policy*. Phase 14's revision log went further and called it "the cheapest item
and the most self-contained". Both are claims, and Phase 15 was taken to grade
them — the same reason FSRS was taken first and SQL drills second.

Three clauses, and the code says something different about each.

**Hints.** `AttemptPolicy` already carries the hint list, copied from the
exercise when the `Attempt` is constructed, and `Attempt.reveal_next_hint`
already refuses once the list runs out. A policy built with an empty list needs
no new enforcement anywhere.

**The clock.** `suggest_grade` has compared `attempt.elapsed(finished_at)`
against `timedelta(minutes=exercise.estimated_minutes)` since Phase 9. A
deadline derived from `estimated_minutes` is therefore a number the grading rule
already reads.

**Test peeking.** This one does not fit. `adapters/sandbox/provisioner.py`
copies a kata's `tests.py` into the workspace, and `adapters/kata/pytest_runner.py`
runs `pytest` against it *from there* — so the file has to exist in the
workspace while the solver works. The workspace is a directory on the solver's
own machine. And §8.1 settled in Phase 3 why that cannot be fixed, in the
sentence `adapters/sandbox/command_policy.py` opens with: **"Two jobs, and
neither is security. The solver authored the content and owns the machine."**

So the honest question is not *how do we hide the tests* but *what is interview
mode actually offering*, given that it cannot hide them.

## Decision

**Interview mode is `AttemptMode`, a field on `AttemptPolicy`, chosen once when
the attempt is opened and stored with it.** `StartAttempt` takes the mode;
nothing else does. `practice start --interview` and a checkbox on the Start form
are the two ways to choose it.

**It withdraws affordances and says that is what it does.** The predicate is
named `AttemptPolicy.reveals_workspace`, not `hides_tests`:

- Hints are withheld by building the policy with none.
- A deadline is set to the author's own `estimated_minutes` — not a multiple of
  it — and the mode and the deadline move together in both directions, so
  neither can exist without the other.
- `load_solution_file` refuses, which withdraws own-editor mode from both the
  browser and the watch stream, and `practice start`'s next-step line stops
  naming the workspace path.

**A late submission is recorded, not refused.** The deadline produces a reading
of a finished attempt — the core bet applied to the clock — rather than a gate
that would destroy the work when it closed.

**The clock is server-rendered on page load and is not a live countdown.**

## Consequences

**What this buys.** Interview conditions on all 62 shipped exercises, with no
new exercise kind, no new port and no new adapter. The grading rule is untouched:
a timed attempt is read by the rule Phase 9 wrote, because the deadline is the
number that rule already compared against. The mode cannot be renegotiated
mid-attempt, cannot differ between the processes that `resume` and `submit` an
attempt, and is readable in the database as the word `interview`.

**What it costs.**

1. **Three of the menu's four words were affordable and one was not.** "Timed"
   and "no hints" are in; "no test peeking" ships as *no path to the workspace*,
   which is strictly weaker. A solver who knows where the cache directory is can
   read the tests, and the tool says so rather than implying otherwise.
2. **Migration 0003**, and the asterisk ADR 0008 predicted for a scheduler holds
   for a mode: a new field on a stored aggregate has to be named where rows are
   built. Two lines in the mapper, two in the column tuple.
3. **The menu's "application-layer policy" is not quite right.** Nothing under
   `adapters/` changed, so it is closer to right than ADR 0019's prediction was
   — but the reason nothing changed is that the sandbox clause was *dropped*,
   not that it was free. An honest reading is that the cheap version of this
   feature is application-layer and the version the menu described is not.
4. **One existing message became a lie and had to be fixed.** `"no hints left:
   this exercise has 0"` is false under interview mode, where the exercise has
   four and the mode is keeping them.
5. **One existing sentence was quietly meaningless and nothing could have caught
   it.** The review panel printed "passed clean, inside the estimate, no hints"
   for an attempt that was never offered one — the Phase 13 ease-factor finding
   repeating exactly, a field present, correctly formatted and empty of meaning.
   `hints_offered` is the denominator it needed.

## Alternatives considered

**Hide the tests for real, by moving `tests.py` out of `repo/` under interview
mode.** The closest to winning, and the one worth the most as a record. It is
buildable: `WorkspaceLayout` grows a directory, the provisioner puts the file
there, and the kata runner points `pytest` at it. It was rejected on two counts.
It needs `SandboxProvisioner.provision` to take the policy — a widened port, for
one caller, to serve one mode — and it changes the kata engine's file layout for
every attempt in order to change what one mode shows. And it still would not
achieve containment: `pytest` must be able to read the file, so it is still on
disk, still under the solver's own user account, one `find` away. **Paying a port
widening for a boundary that is not a boundary is the worst trade in the
phase.** Phase 15's third clause stays an affordance withdrawal, and if a future
phase wants the stronger version it should want it for a stated reason that this
record does not have.

**A `bool` on the policy instead of an enum.** Reads the same in Python and
migrates badly: a third set of rules — a warm-up with hints but a clock — arrives
as a second boolean, and two booleans encode four states of which two are
meaningless. `StrEnum` also makes the stored value readable rather than a `0`
nobody can interpret.

**An environment variable, like `PRACTICE_SCHEDULER`.** Rejected on the reasoning
`config.py` already gives for why the scheduler *is* one: a scheduler must not
vary per invocation, because a card scheduled by one algorithm and moved by
another has a history nobody can reason about. Interview mode is the exact
opposite — it is chosen for this sitting, at this exercise — so the per-attempt
record is the right shape and the env var would be the wrong one.

**Refusing a submission after the deadline.** Rejected because it destroys work
to enforce a rule the core bet says to grade instead. A solver who ran over has
produced an end state, and the end state is what this project grades; a gate that
threw it away would make the tool hostile in exchange for a number
`suggest_grade` can read anyway.

**A live JavaScript countdown.** Rejected as the one number on the page that
nothing grades. It would tick past zero and change nothing, because what decides
an overrun is `elapsed` at submission. Phase 13 found exactly this defect in the
schedule panel's ease factor — present, correctly formatted, meaningless — and a
clock that looks authoritative and is decorative is worse than a stated fact with
"as of this page load" next to it.

**`--interview` on `practice solve` as well as `practice start`.** Rejected
because `solve` has no *during*: it opens an attempt, grades the answer already
written, and exits. Every clause of the mode is about what happens between those
two moments, so the flag would record rules nothing could have applied.

**A separate `ExerciseMode` or a per-exercise `interview:` field in the content
schema.** Rejected because the mode is a property of an *attempt*, not of an
exercise. The same exercise is worth doing both ways, and the content is data
about the problem rather than about how someone chose to sit it.

## Revisit if

- **A solver reports that reading the tests is actually tempting them.** That is
  the evidence the stronger version is missing, and it would justify the port
  widening this record rejected. Until somebody has been tempted, hiding the file
  is a cost paid against a hypothesis.
- **A third set of rules is wanted** — a warm-up with hints and a clock, or an
  untimed no-hints run. The mode-and-deadline pairing guard in
  `AttemptPolicy.__post_init__` is the one line that has to change, and it should
  change with the feature that wants it rather than in advance.
- **The deadline wants to stop being `estimated_minutes`.** If interview attempts
  routinely overrun by a wide margin, the estimate is wrong for interview
  conditions and the library's own numbers are the thing to fix — not a
  multiplier applied here, which would grade against a number no exercise states.
- **A review log arrives.** `hints_offered` exists because a surface needed a
  denominator; if attempts are ever aggregated over time, "no hint was on offer"
  becomes a dimension of the data rather than a detail of one sentence.
