# 0014 — A hand-ordered curriculum manifest, not a prerequisite graph

- **Status:** accepted
- **Date:** 2026-10-03
- **Phase:** 11 (content build-out)

## Context

PLAN.md §15 question 4 asks: *hand-ordered tracks, or prerequisite-graph
unlocking?* and answers "start hand-ordered; revisit once there are 50
exercises". There are now fifty-four, so this is the revisit.

What "hand-ordered" meant until now is the uncomfortable part. Nothing was
ordered by hand. `FilesystemContentRepository.list_exercises()` returned
`sorted(ExerciseId)`, and every surface that shows the library inherited it —
the browse page, and the unscheduled half of the review queue, which is *most*
of that queue on a fresh install (`review_queue.py` says so).

At three exercises alphabetical order was invisible. At fifty-four it is the
first thing a solver sees, and it is actively misleading:

```
git/amend-the-last-commit          <- reasonable first git exercise, by luck
git/cherry-pick-a-fix-to-a-release-branch
git/drop-a-secret-from-a-commit
git/find-the-commit-that-removed-a-line
...
katas/climbing-stairs              <- after edit-distance and knapsack
katas/coin-change
katas/count-islands
katas/detect-a-cycle-in-a-linked-list
katas/edit-distance                <- the hardest kata in the library, 5th
```

`edit-distance` before `climbing-stairs`, `knapsack` before `maximum-subarray`,
a hard rebase-recovery scenario before `amend`. The ordering is an artefact of
spelling.

Two further constraints shape the answer:

- **An exercise id is exactly `<track>/<slug>`** and the loader enforces two
  path segments (PLAN.md §4.1). So the filesystem can express exactly two
  "tracks", `git` and `katas`, while the pedagogical grouping Phase 11 actually
  has is nine runs — history rewriting, recovery, conflicts, search, three kata
  families. Directories cannot carry it.
- **Difficulty is already a field** (`intro`/`easy`/`medium`/`hard`), so sorting
  by it is available and nearly free.

## Decision

**A hand-written `content/curriculum.yaml` declares the order, and
`validate_library` holds it to covering the library exactly.**

- Tracks are listed in order; each lists its exercises in order. Nine tracks
  over fifty-four exercises.
- `FilesystemContentRepository.list_exercises()` returns the library in that
  order. Every caller that offers exercises to a human inherits it, and no
  caller changed to get it.
- **Validation requires the manifest to list every exercise exactly once and
  nothing that is not on disk.** An exercise added without a line in the
  manifest fails `practice validate` and CI.
- An unlisted exercise sorts *last* at runtime rather than raising, so someone
  mid-draft finds their new exercise at the bottom of the library rather than a
  library that will not load.
- Tracks are interleaved across kinds on purpose: git and katas alternate, so a
  solver working down the list meets both rather than spending a fortnight on
  one.

## Consequences

**What it buys.**

- An order someone chose, in a file they can read and argue with, next to the
  content it orders. Reviewing it is reading one file.
- The nine-track grouping exists without moving a single exercise on disk, which
  is the content-as-data bet (ADR 0004) holding up under a second, finer
  structure than the one the ids encode.
- `review_queue.py` got a better answer without changing: it asks the library for
  the library's order, and declining to invent a local ordering is what made that
  possible. The parked question in its docstring is now answered.
- The validation rule is what makes the manifest trustworthy rather than
  decorative. An ordering that silently omits last week's exercise is worse than
  no ordering, because it looks deliberate.

**What it costs.**

- **A second place to edit when adding an exercise.** This is the real cost. It
  is mitigated by being a hard failure rather than a drift — `practice validate`
  names the exercise that is not listed — but "content is data, adding an
  exercise needs no code" is now "adding an exercise needs no code and one line
  in the manifest".
- The order is one person's judgement with no evidence behind it. Nothing
  measures whether `coin-change` before `meeting-rooms` helps anyone.
- `FilesystemContentRepository` now fails to list anything if the manifest is
  missing or malformed, which is a new way for the whole library to break. The
  alternative — fall back to alphabetical — would silently restore the accident
  this replaces, so the failure is deliberate and loud.
- Nothing in the UI *shows* the tracks yet. The manifest orders the library and
  does not group it on screen, so the nine track titles are currently read by
  the validator and by whoever opens the file. Grouping the browse page by track
  is the obvious next step and is not taken here.

## Alternatives considered

**Prerequisite-graph unlocking** — each exercise declares what must be passed
first, and the queue hides the rest. Rejected for this phase, not permanently.
It needs the attempt history as an input to the review queue rather than just the
card store, it needs a cycle check over content (which the library already has an
assertion family for), and it changes the tool from advising to *gating*. Gating
is a product decision with a real downside — a solver who wants `edit-distance`
today should be able to have it — and nothing in fifty-four exercises demands it.

**Sort by difficulty, then by id.** Nearly won, because it is free and needs no
file. Rejected because difficulty is a single scalar and the ordering needs two
dimensions: `coin-change` and `merge-intervals` are both `medium` and want to be
met in a particular order, since one leans on prefix sums and the other on
sorting. It also cannot interleave git and katas, and cannot express that
`climbing-stairs` is the right first DP exercise despite being `easy` and
therefore sorted with eight unrelated things.

**Order by a `sequence:` integer in each `exercise.yaml`.** Rejected: the order
is then spread across fifty-four files, renumbering to insert one exercise edits
dozens, and no single file shows the curriculum. The information is about the
*library*, so it belongs in a library-level file.

**Nested directories for the nine tracks** — `content/git/recovery/...`.
Rejected because it breaks the `<track>/<slug>` id rule, which is load-bearing:
the id *is* the content path (PLAN.md §4.1), and `validate_library` reports a
nested exercise as misplaced precisely so that it cannot happen by accident.
Changing the id shape to carry pedagogy would make every id longer and every
stored attempt's exercise id a migration.

## Revisit if

- Someone wants the library **grouped** rather than merely ordered — a browse
  page with nine headings. The manifest already carries the track titles for it;
  what it needs is a port method and a template, and at that point the `Track`
  type stops being an adapter detail.
- The library passes roughly a hundred exercises, where a single flat order
  probably stops being readable and per-track entry points start to matter more
  than the global sequence.
- Evidence appears that solvers get stuck in a way an ordering could fix —
  `practice progress` already records attempts per exercise, so "everybody fails
  X before Y and succeeds after" is a measurable claim, and the first one that
  would justify gating.
