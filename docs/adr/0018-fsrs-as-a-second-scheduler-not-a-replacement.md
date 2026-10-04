# 0018 — FSRS as a second scheduler, not a replacement

- **Status:** accepted
- **Date:** 2026-10-04
- **Phase:** 13 (stretch — the `Scheduler` port, cashed in)

## Context

[ADR 0008](0008-sm2-first-with-fsrs-behind-a-port.md) shipped SM-2 as the only
scheduler and made two checkable predictions about the day FSRS arrived:

> **Ship SM-2 — the four-grade variant — as `Sm2Scheduler`, behind the
> `Scheduler` port, as the only implementation.** FSRS, if it ever arrives, is a
> second class satisfying the same protocol and one line in `composition.py`.

and, about the card:

> `ReviewCard` does carry `ease`, `interval_days`, `reps` and `lapses`, which is
> the concession: those are SM-2's state, and FSRS would want stability and
> difficulty instead. [...] an honest migration would add columns rather than
> reuse them.

PLAN.md §13 then set the terms this phase was judged on: each stretch item is
*"intended to be an adapter or content addition, not a rewrite — which is the
real test of whether the architecture earned its keep"*. And §13's standing rule
says a port needs at least two real or test implementations or it gets deleted —
which `Scheduler` had been satisfying on an IOU, with one real implementation
and a double that does no arithmetic.

Three things were therefore genuinely unknown, and none of them is "is FSRS
better".

1. **Whether the protocol holds.** `next_card(card, grade, now) -> ReviewCard`
   speaks in cards and grades and says nothing about ease factors. That is easy
   to write and easy to be wrong about: a port is only as abstract as the
   *second* implementation proves it to be.
2. **Whether the four properties PLAN.md §9.7 states are properties of a
   scheduler or of SM-2.** With one implementation there was no way to find out,
   and the question matters — a property believed to be universal and actually
   local is a constraint that will one day be enforced against something it was
   never true of.
3. **What a mid-history switch does.** The tool stores one row per exercise and
   no review log, so a user who changes algorithm has a card written by one and
   about to be read by the other.

## Decision

**Ship `FsrsScheduler` (FSRS-4.5) beside `Sm2Scheduler`, selected by
`PRACTICE_SCHEDULER`, with SM-2 still the default.** Both satisfy the unchanged
`Scheduler` protocol; `composition.py` holds the only mapping from a name to an
implementation.

Five decisions follow, and each of them is a place the port's vocabulary had to
be paid for.

**`ReviewCard` gains `stability` and `difficulty`, nullable, in migration
0002.** ADR 0008's prediction, taken rather than dodged. The rejected
alternative was to overload `ease` as "whatever the scheduler's primary number
is": free to write, and it makes every reader of a card wrong — the floor of 1.3
is SM-2's and means nothing on a 1-to-10 difficulty scale, so the schema's
`CHECK (ease >= 1.3)` would have begun refusing valid FSRS state, and a card
written by one scheduler and read by the other would be silently misinterpreted
rather than visibly empty. Nothing is backfilled: a stability invented for a
card with three SM-2 reviews behind it is a fabricated memory model dressed as a
migration. `has_memory_state` is `False` for every row a database SM-2 filled,
and that is the honest reading of `NULL`.

**A switch adopts the history rather than resetting it.** At the default 90%
retention an FSRS interval *is* its stability — exactly, because
`0.9 ** -2 - 1 == 0.19 / 0.81 == 19 / 81`, which is the forgetting curve's own
factor, so the two cancel by construction. That identity is what lets a card
SM-2 left at fifteen days be read as a card with a stability of fifteen. The
rejected alternative was to treat an unknown memory state as a new card, which
would have thrown away a month of real review history on the day the choice was
changed, and done it invisibly.

**SM-2's `ease` is left untouched by FSRS, and FSRS's two columns by SM-2.**
Which is what makes the switch reversible in both directions rather than one.

**Three of §9.7's four properties are the port's; one is SM-2's.** The ease
floor, monotonicity under consecutive `GOOD`, and `due_on` always falling after
the review are held against both implementations in
`tests/unit/domain/scheduling/test_scheduler_conformance.py`. *"`AGAIN` always
resets to one day or less"* is SM-2's policy and stays in `test_sm2.py`: FSRS
schedules a lapse from its own post-lapse stability, which on a card established
for a year is weeks. What replaces it as a shared property is the weaker
**a lapse never lengthens an established interval**.

**Where FSRS-4.5's formula and that property disagree, the property wins.** The
published post-lapse term can exceed the input stability where stability is
small, so `FsrsScheduler` clamps it. The rejected alternative was to let the
model say what it says and weaken the property to fit; a scheduler that
lengthened the interval because the solver had forgotten the answer is wrong in
the way users notice, and fidelity to a formula whose seventeen parameters this
project cannot fit anyway is not worth that.

## Consequences

**What it buys.**

- **The port is no longer a claim.** Two real implementations and a double, which
  is what §13 asks, and the protocol did not move by a character to admit the
  second.
- **The §9.7 question is answered**, and a shared conformance suite is now the
  place any third scheduler would be held. `test_every_real_scheduler_is_covered_here`
  is the guard, because a scheduler added and not parametrized in is one nothing
  holds to the contract and no other test would notice.
- **A finding that generalises.** §9.7's interval clamp reads like a quirk of
  SM-2's arithmetic — at the ease floor, `round(1 * 1.3) == 1`. FSRS stalls too,
  for an unrelated reason: stability grows by `1 + k * (exp(w10 * (1 - R)) - 1)`,
  which is exactly 1 when `R == 1`, and `R` is 1 whenever no days have passed.
  Two causes, one fix. **The clamp belongs to whole-day intervals, not to SM-2**,
  and only a second implementation could have shown that.
- **A defect the test suite could not see.** The schedule panel printed
  `Ease 2.50` unconditionally — correct under SM-2, meaningless under FSRS, and
  present and correctly formatted either way, so no fragment assertion in
  `tests/web/` was ever going to fail on it. Found by switching the scheduler and
  reading the page, which is the same way Phase 9 found four quiet buttons and
  Phase 12 found an em dash on a Windows console.
- **The seam for fitted parameters exists.** `weights` is a constructor argument,
  so a parameter set fitted to a real log arrives without touching a line of the
  arithmetic.

**What it costs.**

- **`ReviewCard` is now wider than either scheduler needs**, and a reader has to
  know which fields belong to which. Three invariants hold the shape together —
  stability positive, difficulty on its scale, and the pair set together or not
  at all — stated in the dataclass and restated in the schema. The pairing is the
  one worth naming: having *no* memory state is ordinary, having *half* of one is
  a mapper that dropped a column.
- **The seventeen parameters cannot be validated here, and that has not
  changed.** ADR 0008's first constraint still binds: `sqlite/reviews.py`
  replaces a card on every review and keeps no history, so there is no log to fit
  against and none to compare with. The defaults are carried as data under one
  name; the *formulas* are what the tests hold, over every card the schema can
  store. The first intervals (1, 1, 4, 14) and initial difficulties are pinned to
  literals as the one cheap check that the weights are in the order the module
  reads them in — a transposition in the first four would show up as a first
  review due in a fortnight. **FSRS used with unfitted parameters is FSRS without
  the thing that makes it better than SM-2**, which is the honest summary and the
  reason the default did not move.
- **`SCHEDULERS` is a two-entry mapping**, which is close to the abstraction §13
  says to delete. It earns its place on one thing an `if` would not do: it is the
  list of valid names, which the refusal quotes and `practice up` prints.
- **A fifth preflight step** on a module whose docstring argued for four.
- **No maximum interval**, which FSRS implementations normally have.
  `min(ceiling, ...)` and `max(previous + 1, ...)` cannot both hold, so a ceiling
  would break the monotonicity property the moment a card reached it. The port
  has nowhere to express one and `ReviewCard` puts no upper bound on
  `interval_days` either, so the exposure is shared with SM-2 rather than new.

**The honest verdict on ADR 0008's prediction.** The line in `composition.py`
was exactly where it said, and the migration was exactly what it said. What it
did not foresee is that a second implementation nobody can *select* is written
rather than shipped — so the real cost was one line plus a registry, a config
question, a preflight step and a template branch, all four of them in the
interface and at the root.

Measured rather than asserted: twelve files under `src/`, and **not one of them
a use case, a grader or a route.** `application/`, `domain/checks/` and the
sandbox, git, kata and content adapters are untouched. The SQLite mapper and the
review repository each gained the two column names, which is the one place the
"adapter addition, not a rewrite" bar of PLAN.md §13 is met by an *edit* rather
than an addition — a new column has to be named where rows are built, and ADR
0008 predicted that half of the bill explicitly.

## Alternatives considered

**Replace SM-2 outright.** The smaller diff, and it was rejected on two counts.
It deletes the only scheduler whose behaviour is explicable to the person using
it — "you got it right twice, so it doubled" — and replaces it with seventeen
numbers nobody here can justify. And it would have destroyed the experiment: the
value of this phase is the *comparison*, and a replacement leaves one
implementation again, with the §9.7 question still open and the port still
unproven.

**FSRS-5 or FSRS-6 rather than 4.5.** Better algorithms, and the same
unfittable-parameter problem one version further from the published defaults
most implementations have been checked against. 4.5 is the version whose
formulas can be written down in forty lines and held to properties; the newer
ones add short-term-memory handling for intra-day reviews, which is a feature for
a flashcard app doing twenty cards a minute and not for a tool where one review
is a solved git scenario.

**Make it a CLI flag rather than an environment variable.** Rejected because a
scheduler must not vary per invocation. A card moved by one algorithm and then
the other is handled deliberately, but a history where that happened at random
because of which flag was typed is not a history anybody can reason about. An
environment variable is also the only persistent setting this tool has, there
being no config file — which is a constraint, not a preference.

**Default to an unknown name instead of refusing it.** A typo in
`PRACTICE_SCHEDULER` that quietly kept scheduling with SM-2 is indistinguishable
from having set nothing, and the symptom arrives weeks later as an interval the
user cannot explain. The scheduler is already the component whose
misconfiguration is hardest to see; a silent fallback would make it invisible.

**Add a review log in this phase so the parameters could be fitted.** The thing
that would actually make FSRS worth defaulting to, and out of scope by a wide
margin: it is a schema change, a repository method, a backfill with nothing to
backfill from, and a fitting procedure — which is a phase, not an afternoon. ADR
0008 already records the standing cost of not having one, and this phase adds a
reason to pay it rather than paying it.

## Revisit if

- **A review log exists.** Then the parameters can be fitted to this user's own
  history, which is the entire reason FSRS is better than SM-2, and the default
  should move. Until then it should not.
- **A third scheduler is wanted.** The conformance suite is the thing to read
  first, and `SCHEDULERS` the thing to add to; if a third implementation cannot
  satisfy the four shared properties, the finding is about the properties, the
  way this phase's finding was.
- **Anything outside `interface/` and `composition.py` has to change to admit
  one.** That would mean the port stopped being a seam, and the right response is
  a new ADR saying what leaked rather than a widening of this one.
- **A user asks to tune the retention target.** It is `_DESIRED_RETENTION`, it is
  deliberately not exposed, and exposing it needs an answer to the drift it
  creates: an interval computed under one target sitting next to a stability
  fitted under another.
