# 0001 — Record architecture decisions

- **Status:** accepted
- **Date:** 2026-09-30
- **Phase:** 0

## Context

This project is being built partly to be read: by a future me picking it back up
after a gap, and by an interviewer who has fifteen minutes and no intention of
reading 1,400 lines of plan. Several of its decisions are load-bearing and
non-obvious — grading by repo state, no containers, no ORM, no npm — and each has
a defensible alternative that was rejected for a specific reason.

Those reasons decay fast. A month later the code shows *what* was built, git
history shows *when*, and the *why* is gone. The failure mode is concrete:
someone (me) sees the sandbox running subprocesses in temp directories, thinks
"this should obviously be a container", and spends a session rediscovering the
constraint that ruled it out.

`docs/PLAN.md` is not a substitute. It describes the intended end state and gets
edited in place as thinking changes, so it cannot hold the history of what was
considered and dropped.

## Decision

Keep numbered, append-only ADRs in `docs/adr/`, in the Nygard style, using
[`template.md`](template.md). Write each one in the phase where the decision is
actually made. Every ADR carries an **Alternatives considered** section and a
**Revisit if** section; both are mandatory, not optional garnish.

A reversal is a new ADR that supersedes the old one. Nothing is edited into
retroactive correctness and nothing is deleted.

## Consequences

- The record of rejected alternatives survives, which is the part that is
  otherwise unrecoverable and — in an interview — the part that shows judgment
  rather than familiarity.
- **Revisit if** turns each decision into something provisional on stated
  conditions instead of permanent by accident.
- Ongoing cost: a real one. ADRs written for their own sake are worse than none,
  so scope is limited to decisions that are expensive to reverse or that the code
  cannot explain by itself. Library picks that could be swapped in an afternoon
  do not get one.
- Some duplication with PLAN.md §12, which keeps the summary table. Accepted: the
  table is the map, the ADRs are the territory.

## Alternatives considered

- **PLAN.md alone.** Closest to winning, and the reason it loses is structural
  rather than stylistic: it is edited in place, so it always reads as though the
  current design were the only one ever contemplated. It answers "what" well and
  "why not" not at all.
- **Long commit messages.** Genuinely good, and used here in addition — but
  discoverable only if you already suspect which commit to read. There is no
  index of decisions in `git log`.
- **A wiki or issue tracker.** Splits the reasoning away from the code it
  explains, and rots on a schedule set by someone else's hosting.
- **Comments at the decision site.** Works for local choices; cannot express a
  decision that spans four packages, and there is no natural file in which to
  say "we rejected containers".

## Revisit if

The ADRs stop being written in the phase where the decision happens. An ADR
backfilled three phases later is a summary of the code, not a record of a
decision, and at that point the practice is costing time without buying anything.
