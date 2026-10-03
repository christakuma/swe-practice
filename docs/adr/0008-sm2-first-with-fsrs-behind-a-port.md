# 0008 — SM-2 first, with FSRS behind the same port

- **Status:** accepted
- **Date:** 2026-10-02
- **Phase:** 9 (spaced repetition and progress)

## Context

A practice tool that grades the end state still has to decide *when to show you
the exercise again*, and the answer is the difference between a quiz app and a
training system. Two families of algorithm are available.

**SM-2** is the 1987 SuperMemo algorithm, and the four-grade variant Anki
popularised is what most people have actually used. It is about forty lines: an
ease factor per card, two learning steps, and a multiply. Every one of its
numbers is a constant somebody chose, and it is comfortably beaten on
retention-per-review by anything modern.

**FSRS** is the current state of the art — a three-component memory model
(difficulty, stability, retrievability) with seventeen parameters fitted to a
corpus of real review logs. Used with the published default parameters it is
better than SM-2; used with parameters fitted to *your own* history it is better
again, which is the whole point of it.

Three constraints bear on the choice here, and none of them is about which
algorithm is better.

1. **There is no review history to fit anything to.** FSRS's advantage comes
   from optimisation against a log of real reviews, and this project has none —
   not even a schema for one. `sqlite/reviews.py` stores one row per exercise
   and replaces it on every review, which was a deliberate Phase 6 decision: a
   review *log* is a table nothing in the MVP reads.
2. **The scheduler is the easiest thing in the system to get wrong quietly.** An
   interval that is subtly bad produces a tool that feels fine and teaches
   badly, and nothing fails. The only defence is properties — `ease` never below
   1.3, consecutive `GOOD` strictly increasing the interval, `AGAIN` always
   resetting — and those are properties of SM-2 as stated. FSRS's are harder to
   state and much harder to hold a hand-written implementation to.
3. **The library is tens of exercises, not thousands of cards.** The gap between
   the two algorithms is a review-efficiency gap. At this size, the cost of
   scheduling slightly too often is minutes a week.

## Decision

**Ship SM-2 — the four-grade variant — as `Sm2Scheduler`, behind the `Scheduler`
port, as the only implementation.** FSRS, if it ever arrives, is a second class
satisfying the same protocol and one line in `composition.py`.

Three things follow from "behind the port" being a real claim rather than a
gesture:

- **`GradeReview` is the only use case that holds a `Scheduler`.** Nothing else
  in the system has the port in a signature, so the blast radius of swapping it
  is one constructor argument at the composition root.
- **The port speaks in cards and grades, not in SM-2's vocabulary.**
  `next_card(card, grade, now) -> ReviewCard` says nothing about ease factors or
  learning steps. `ReviewCard` does carry `ease`, `interval_days`, `reps` and
  `lapses`, which is the concession: those are SM-2's state, and FSRS would want
  stability and difficulty instead. They are nullable-in-spirit — an FSRS
  implementation can leave `ease` at its default and ignore it — but an honest
  migration would add columns rather than reuse them.
- **The floor on `ease` is enforced by `ReviewCard`, not only by the
  scheduler.** An invariant that holds while one function is the sole writer is
  not an invariant; a repository is also a writer, and the schema restates the
  same `CHECK (ease >= 1.3)` for the same reason.

Four grades rather than SM-2's original six. The published algorithm asks the
learner to distinguish "incorrect, but it felt familiar" from "incorrect, and
the right answer seemed easy once seen", which nobody can do honestly about a
git exercise they have just finished — and a scale people cannot use produces
noise the arithmetic then takes seriously.

## Consequences

**What it buys.**

- The whole scheduler is forty lines of pure arithmetic with no I/O, so it is
  property-tested by hypothesis over thousands of generated cards rather than by
  three examples.
- Its behaviour is explicable to the person using it, which matters here more
  than in a flashcard app: this tool *shows* its suggested grade and the reading
  behind it, and "passed, but one hint, so one step down" is a sentence a solver
  can argue with. The equivalent sentence for FSRS is "the model says 11 days".
- Swapping it is a change to `composition.py` and a new module. The port was
  declared in Phase 1 with every other protocol and now has two implementations
  — `Sm2Scheduler` and the test double — which is what PLAN.md §13 asks before a
  port is allowed to exist at all.

**What it costs.**

- Measurably worse scheduling than FSRS. More reviews for the same retention;
  the published comparisons put the gap in the tens of percent.
- The constants are inherited, not derived. `HARD` multiplying by 1.2, `EASY`
  adding a 1.3 bonus, the 1/6-day learning steps — these are Anki's defaults and
  this project has no evidence for or against any of them.
- **The card keeps no history, so there is nothing to evaluate the scheduler
  against.** This is the cost that compounds: `reps` and `lapses` are derivable
  from a review log and a review log is not derivable from them, so every day
  the tool runs without one is a day of evidence that cannot be recovered. That
  is a cheap thing to fix later only in the sense that the table is easy to add;
  the data is not.
- `ReviewCard` is shaped like SM-2's state, so an FSRS implementation would
  either carry fields it does not use or need a migration.

## Alternatives considered

**FSRS now, with the published default parameters.** The closest to winning, and
rejected on constraint 2 rather than on effort. A hand-written FSRS whose
power-law is subtly wrong produces plausible intervals and no failing test; the
honest way to ship it is to depend on the reference implementation, which is a
package, and the project's offline rule makes a dependency a thing to be sure
about rather than a thing to try. Worth revisiting the moment there is a log to
fit against — at which point FSRS is clearly better *and* checkable against this
tool's own history rather than against a paper.

**No scheduler: sort the library by what you have failed.** Genuinely tempting,
because `SummariseProgress` computes exactly that and the dashboard could rank
by it in one line. Rejected because it answers a different question — it is a
weakness report, not a *schedule*, so an exercise you got right stays at the
bottom forever and is never re-tested. Forgetting is the thing spaced repetition
exists to handle and "what did I fail" cannot see it.

**A fixed ladder — 1, 3, 7, 14, 30 days, reset on failure.** Half the code of
SM-2 and about as good at this library size, which is an argument for it. It
loses the per-card ease factor, and the ease factor is the one piece of SM-2
that adapts to *this* exercise being hard for *this* person rather than to the
schedule being early. Keeping it costs one float and one clamp.

**Six grades, as SM-2 originally specifies.** Rejected on the input side rather
than the arithmetic: the extra resolution is self-reported, and self-reporting
is already the weakest signal in the system. Four buckets are also what a
verdict can distinguish, which is what makes the automatic suggestion possible
at all — and the suggestion is a better signal than the sixth grade would have
been.

## Revisit if

- A review log exists with a few hundred entries in it. That is the point at
  which FSRS can be *fitted* rather than merely installed, and at which this
  tool can measure the swap rather than trust a paper.
- The library passes a few hundred exercises, where the review-efficiency gap
  stops being minutes a week.
- The properties in PLAN.md §9.7 stop being the ones that matter — if, for
  instance, the tool starts scheduling by estimated time rather than by card, the
  monotonicity property is no longer the invariant worth holding.
