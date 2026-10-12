# 0025 — Tracks are a second manifest, read off the attempt log and carried in the URL

- **Status:** accepted
- **Date:** 2026-10-12
- **Phase:** 20

## Context

The report was *"this doesn't seem to have persistent memory"*, and it was
wrong about the storage and right about the product. Every attempt had been
written to SQLite since Phase 6. Nothing on screen could be asked about it **by
exercise**:

- `/browse` looked the same on the fortieth visit as on the first.
  `routes/browse.py` argued, in Phase 9, that status did not belong there
  because *what should I do* was the dashboard's question and *where am I
  losing it* was `/progress`'s. That missed a third question — *which of these
  have I done* — which is about that list and no other page.
- The dashboard marked an exercise **new** whenever it had no review card. A
  card is written when a schedule grade is pressed, so an exercise solved and
  then walked away from came back marked new a minute later.
- The only way on from a finished attempt was a "Back to the queue" link that
  appeared *inside* the schedule block after a grade was pressed.

Three requests followed from it: show what has been done and when, a button
that goes to the next question, and tracks — *the Blind 75*, *git scenarios* —
with an order that makes sense.

The constraint that shaped the answer is that [ADR
0014](0014-a-hand-ordered-curriculum-manifest.md)'s `curriculum.yaml` names
every exercise **exactly once**, and `practice validate` enforces it. That is
what makes it an order. It is also what makes it unable to say that Two Sum is
step 1 of one route and step 2 of another.

## Decision

**Three decisions, one per request, and each is about where a fact is read
from.**

1. **Done is read off the attempt log, never off the card store.**
   `application/tracks.records_of` reduces the graded attempts to one `Record`
   per exercise — how many, how many passed, when last, when last passed — and
   every list that shows an exercise shows it. *Done* means passed at least
   once and stays meant: a later failure is visible as the last attempt and
   does not reopen the step.

2. **A track is a second manifest, `content/tracks.yaml`**, beside the
   curriculum and not inside it. A track is a named selection with an order of
   its own, in one of two spellings: an explicit `exercises:` list, or
   `follows: curriculum` for every exercise in the curriculum's order. It
   reaches the application through one new method on an existing port,
   `ContentRepository.list_tracks`, already resolved to ids. The first track
   declared is the default.

   **What makes an order *sensible* is a rule, not a review.** `practice
   validate` holds every explicit track to this: two exercises from the same
   curriculum section keep the order that section gives them. Inside a section
   the order is dependency, and it is argued once, in `curriculum.yaml`.
   Between sections a track is free, and both hand-ordered tracks use that —
   the curriculum interleaves kinds for a solver doing all three, and a solver
   doing one kind is better served by a difficulty curve.

3. **Which track an attempt is on is carried in the URL and stored nowhere.**
   `/attempt/{id}?track=blind-75`. The form that starts an attempt posts the
   name, the redirect puts it in the query string, both submit forms post it
   back, and the Next button under the verdict posts it on. `NextExercise` then
   returns the first unfinished step *beyond* the one just attempted, wrapping.

## Consequences

**Bought.**

- No migration, no new table, no new port. Twenty-two use cases where there
  were nineteen, and all three new ones are reads over data that already
  existed.
- A solver who skips the schedule buttons still moves along a track, because
  nothing about a track asks whether a card exists. The scheduler keeps its
  one job.
- A reordered curriculum section fails `validate` naming each track that still
  has the old order, instead of leaving a track that quietly teaches it
  backwards.
- Two tabs can be on two tracks. That is how somebody alternating git and katas
  uses this, and it is true by construction rather than by care.

**Cost.**

- **An attempt resumed from the dashboard has lost its track**, because that
  link has no query string. It falls back to the default track, which is a
  worse answer than the right one and a better one than no button.
- **The curriculum's sections are also called tracks**, in `curriculum.yaml`'s
  top-level key and in `adapters/content/curriculum.Track`. That name was taken
  first and is in every pack already written, so it was not renamed, and there
  are now two things called a track: a section of the one order that nobody
  follows, and `domain.track.Track`. The docstrings say which is which. It is a
  wart.
- **`completed()` is read on four pages now, not one**, and it loads whole
  aggregates. `sqlite/attempts.py` already names that as the query that stops
  being free; a local history is hundreds of rows, and the replacement when it
  is not is a projection.
- **The validator's rule cannot see a dependency between sections.** Those are
  a hand-written list of `(premise, lesson)` pairs in
  `tests/content/test_library.py`, checked against every track that holds
  both. The list is as good as whoever maintains it.
- **Dates are UTC**, because `SystemClock` is. "Passed 2026-10-10" for an
  attempt on the evening of the 9th, Pacific time, is the same answer
  `/progress` already gives and for the same reason. Fixing it is a decision
  about the clock, not about this.

## Alternatives considered

**Tracks as a second key inside `curriculum.yaml`.** One file rather than two.
Rejected because the two hold different promises and the validator checks them
differently: the curriculum must name everything exactly once, and a track must
not have to. One file would have had one rule with an exception in it.

**Derive every track's order from the curriculum** — a track as a *set*, walked
in curriculum order. This was the closest to winning: no order to validate,
because there is only one. Rejected on running it. Restricted to the
seventy-five, the curriculum's order opens with two easy katas and then four
mediums, and reaches `contains-a-duplicate` — the easiest problem on the list —
tenth, because the library's own on-ramps to that section (`move-zeroes`,
`longest-common-prefix`) are not among the seventy-five. For git it puts three
mediums and a hard at steps three to six. An order that is right interleaved is
not automatically right filtered.

**A `blind-75` tag on seventy-five exercises.** No new file at all. Rejected
because tags are what mastery is measured by: "weakest tag: blind-75" is not a
thing anybody is weak at, and it would have sat in the tag filter beside
`two-pointers` as if it were a technique.

**Store the track on the attempt.** A nullable column and a migration; it would
survive a closed tab and a dashboard resume. Rejected because it puts
navigation state — which page somebody arrived from — into an aggregate whose
every other field is about the work, and makes `Attempt.restore`, both
repositories and the mapper carry it.

**A persisted "current track".** The dashboard could then say *you are on the
Blind 75*. Rejected because it is one setting and there can be two tabs.

**Next follows the due queue.** The queue is already the tool's answer to *what
should I practise*. Rejected because an exercise leaves the queue when it is
scheduled, not when it is solved: a solver moving quickly would be handed back
what they had just passed. `test_next_moves_on_without_a_schedule_grade` is
that failure, written down.

**A status filter on `/browse`.** Considered and left out, for the reason the
route already gave: it would be the route re-deciding what the repository
returned. Status is *shown* there, which was the half that was missing.

## Revisit if

- **Resuming without a track turns out to matter** — if people start a track,
  close the tab, resume from the dashboard and are surprised by where Next goes.
  The column on the attempt is then the answer, and the migration is small.
- **A third hand-ordered track wants to reverse two exercises inside a
  section.** That means the section's order was not dependency after all, and
  the thing to change is the curriculum's claim rather than the rule.
- **The history gets long enough for `completed()` to show up in a page load.**
- **`/progress` and the record chips are ever given local dates**, in which
  case both change together or neither does.
