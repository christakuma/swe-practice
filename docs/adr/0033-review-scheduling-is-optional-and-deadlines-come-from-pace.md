# 0033 — Review scheduling is optional, and a deadline is computed from pace

- **Status:** accepted
- **Date:** 2026-10-26
- **Phase:** post-26 (a request, not a planned phase)

## Context

Two complaints, both about the shape of the tool rather than a defect.

The due queue, the overdue chips and the Schedule panel after every graded
attempt are the spaced-repetition half of the product. For someone working
through a track they are noise: "Due today" is the first thing on the dashboard
and a grade has to be pressed or ignored after every attempt. Nothing in the app
let that be turned off, because nothing in the app stored a choice at all.

And a track page already listed every step with its own Start button (144 on
`everything`), but the track's title is deliberately not underlined and the only
visible control on a track row was *Continue*, which goes to the first unfinished
step — the opposite of choosing one. The capability existed and could not be
found, and a long list had no way to be narrowed.

A deadline, if offered, has to survive the usual fate of deadlines: invented
once, ignored after a week.

## Decision

- **Review scheduling is a preference, default on, switched on the dashboard.**
  Off hides the due queue, the schedule grade and the wording about both
  (`reviews_enabled()` is a Jinja global read at render time, so no route has to
  remember to pass it). Nothing is deleted: cards stay, and turning it back on
  resumes. The routes still compute the review offer; the guard is in the
  template because `review.html` dereferences it.
- **A `SettingsRepository` port** — `get` / `set` / `delete` over text — with a
  SQLite table (`0006_settings.sql`) and an in-memory twin held to one contract
  test. Keys are interpreted only in `application/preferences.py`.
- **Deadlines are projected, then optionally pinned.** The track page shows
  where the last 28 days' first passes end up (`application/pace.py`) with no
  setup; "Make that my goal" stores that date, or a typed one, under
  `goal:<track>`. With a goal set the page reports days left and the weekly rate
  it needs, flags it when that is 25% above the measured pace, and offers
  *Re-plan from my recent pace* once the day has passed.
- **No projection from fewer than three first passes, none for a finished track,
  and "over a year" instead of a date past 365 days.**
- **Tracks are searchable** by a plain GET form (`?q=`, `?show=todo|done`); step
  numbers stay the track's own. Track rows say "choose a step (N)".

## Consequences

- A person who never touches the switch sees today's app plus a goal block on
  track pages and a search box.
- Goals work with scheduling off, which is the point: they are what replaces the
  queue as a reason to open the tool.
- Pace is per track, so `blind-75` and `everything` count the same pass twice.
  Each is asked how far along *it* is; nothing sums them.
- A goal is a bare date. There is no history of goals, no per-day quota and no
  notification; the cost of that is that nothing nags, which is also the benefit.
- The default is on, so an existing user must press one button to get the
  dashboard they asked for. Flipping the default is a one-line change in
  `reviews_enabled`.

## Alternatives considered

- **A goals table with its own port, use case, state machine and dashboard
  chips.** The first draft of this. A review of it found it over-built for
  "automatically(-ish) create deadlines": the part that matters is the computed
  date, and a user-set date is one string per track. Closest to winning; cut.
- **Per-exercise due dates assigned up front.** That is what the scheduler
  already does and what was being found noisy.
- **Removing scheduling.** The request was optional, not gone, and the SM-2/FSRS
  work (ADR 0008, 0018) is the part of the product that is distinctive.
- **A client-side filter.** New script surface for something a GET form does, and
  the filtered view would not be a link.
- **Minutes-per-day fallback for a brand-new user** (estimate from each
  exercise's `estimated_minutes`). A date from a number the user never gave is a
  guess dressed as a plan; saying "pass a few more steps" is truer.

## Revisit if

Someone wants a goal to *do* something — a reminder, a daily share on the
dashboard — at which point a goal needs more than a date and the table the first
draft proposed is worth having.
