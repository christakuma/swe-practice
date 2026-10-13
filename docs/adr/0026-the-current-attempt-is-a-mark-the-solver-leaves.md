# 0026 — The current attempt is a mark the solver leaves, not something a tutor infers

- **Status:** accepted
- **Date:** 2026-10-12
- **Phase:** after Phase 20

## Context

[ADR 0024](0024-an-mcp-server-that-can-only-read.md) had the MCP server refuse
whenever more than one attempt was open and no id was passed, and list the ids
instead. The reason was sound: *a tutor confidently describing the wrong
repository is the failure this feature exists to prevent.* The cost it named was
"one round trip".

The report, from using it: *"whenever I try the MCP, it claims I have multiple
attempts open."* One exercise left unfinished turns that one round trip into
every round trip. The refusal was written for an unusual state and it is the
usual one, because abandoning an attempt is a deliberate act and leaving one is
not.

Four things were true going in.

**The application knows nothing about which attempt is in front of the
solver.** `ResumeAttempt` and `OpenWorkbench` were both written to write
nothing, and both say why: an event in the log is something the solver *did in
the exercise*, and the advisory checks (§6.3) read it.

**The log cannot answer the question either.** Editing a kata or a drill
records nothing until it is submitted (ADR 0013), so an attempt somebody has
been typing into for half an hour has the same last activity as when it was
started.

**The server must stay read-only.** That is ADR 0024's whole claim, and nothing
here is allowed to weaken it.

**A GET in the web app "cannot change anything".** `interface/web/security.py`
says so in as many words, and the cross-origin guard is built on it: safe
methods are the ones it does not check.

## Decision

**The attempt a solver has in front of them is marked, and the mark is read
rather than inferred.**

**One use case writes it.** `MarkCurrentAttempt` is called by the three
surfaces that put an attempt in front of a person, and by nothing else:

- `practice start` and `practice resume`, after they have done their work;
- an open workbench page, through `static/in-front.js`, which posts when the
  page loads visible and again each time its tab or window comes back to the
  front — `visibilitychange`, `focus` and `pageshow`, one report per time in
  front.

It refuses an attempt that is finished. `StartAttempt`, `ResumeAttempt` and
`OpenWorkbench` do not mark, and go on writing nothing.

**One use case reads it, and holds the whole rule.** `FindCurrentAttempt`
answers, in order: the marked attempt, *whether or not it has been finished
since*, unless it was abandoned; otherwise the only open attempt; otherwise
nothing.

**The mark is one id beside the attempts**, in a one-row table
(`0004_current_attempt.sql`). It is not a field on the aggregate, not a column
`save` writes, and not an event, so the log is what it was.

**The MCP server asks `FindCurrentAttempt` in place of an id**, and when that
finds nothing gives the refusal ADR 0024 wrote, which now also says how to get
out of it. `list_attempts` and `practice attempts` label the current attempt.
The server still writes nothing: it calls no use case that sets the mark.

## Consequences

**What this buys.** With an unfinished attempt lying around, "this" means the
one on screen and a tutor is shown it without asking. With two attempts in two
tabs it is the tab looked at last. And the attempt just submitted is still
"this": *what did I get wrong?* gets the verdict and the author's notes without
an id, where ADR 0024 needed one from the URL. The refusal survives for the one
state where there is honestly nothing to go on.

**What it costs.**

1. **A migration, for one id.** The first schema change that is not about an
   attempt or a card.
2. **The page talks to the server when nothing was clicked.** One POST each
   time a workbench comes to the front, usually writing the id already there.
   It is the first request in the app that a person did not ask for, and the
   first JavaScript of ours that lives in `static/` rather than in a template.
3. **A test that needs node.** The script's behaviour is which events it hears
   and what it does on each, and the only way to check that is to run it, so
   `tests/web/test_in_front_script.py` does — and is skipped where node is not
   installed. A skip is a machine that cannot check. Under `CI` it fails
   instead, so a runner image that loses node turns the build red rather than
   nine tests grey; the workflow does not install node itself, and relies on
   the hosted images carrying it.
4. **"Looked at last" is not "being asked about".** Somebody who glances at the
   other tab and then asks about the first is shown the other. The context
   names its exercise in its first heading, so it is visible rather than silent;
   it is still a wrong answer the old refusal could not give.
5. **A finished attempt holds the mark until something else is in front.** Ask
   a tutor the morning after submitting, having opened nothing since, and it is
   shown yesterday's verdict rather than asked which. That is the mark meaning
   what it says, and it will sometimes be stale.
6. **Two use cases that are a handful of lines each**, twenty-four in all. Each
   decides something — what may take the mark, what "this" means — so neither
   is a forwarder (§13), but the pair is most of a feature's worth of ceremony
   around one id.
7. **Nothing is marked on the day this arrives.** An existing database has
   several attempts open and an empty table, and a tab that was open across the
   upgrade has no script in it. So the first question after upgrading gets the
   old refusal, from a feature whose whole point is that it does not. The
   refusal names both ways out and the README says so first; no migration could
   have chosen for the solver.
8. **A surface that forgets to mark is silent.** Putting the call in three
   places rather than inside the use cases that start and resume is the trade
   the review below made, and the cost of it is that a fourth way to get in
   front of an attempt has to remember.

## Alternatives considered

**Infer it from the log: the open attempt with the most recent event.** No
migration, no write, and the read path stays a read all the way down. Rejected
on the second fact in the context: a kata records nothing between start and
submit, so "most recent activity" is "most recently started" for most of the
library, and it is wrong in exactly the case that matters — going back to the
older attempt. It is also the guess ADR 0024 rejected, with a better heuristic.

**Mark in `OpenWorkbench`, when the page is loaded.** Built first. Rejected on
a question asked while it was being built — *what happens with two problems
open in different tabs?* The mark sat with whichever was loaded last, however
long ago the solver went back to the other, because switching tabs makes no
request. A link opened in a background tab took the mark too. And it made a GET
write, against the fourth fact in the context.

**Mark inside `StartAttempt` and `ResumeAttempt`.** Built second, on the
argument that a rule each surface restates is a rule one of them forgets, and
taken out by a review of the diff. Those two are loaders as well as acts:
`practice solve` starts an attempt and finishes it in one command, and
`practice submit` resumes one in order to grade it, so each took the mark from
the attempt being worked on for one about to be closed. And an advisory write
inside `StartAttempt` could fail a start whose attempt had already been saved.
Cost 8 is what leaving them alone costs.

**Decide it from the open attempts alone** — the marked one if it is still
open, otherwise the only one open. Built with the above and found by the same
review, on the path everybody walks: leave one attempt unfinished, work
another, submit it, and the only attempt still open is the stale one. The tutor
was handed that, with the other's verdict on screen. A flag on each open
attempt also could not say the thing that needed saying, because the attempt
that is current may not be in the list.

**Ask when two attempts are open in different tabs**, which was the suggestion
that came with the two-tab question and is the behaviour one would want.
Rejected because the server cannot tell that state from the one the report was
about. "Open in a tab" is not something a page can keep asserting: a browser
throttles a background tab's timers, then freezes it, then discards it, so a
heartbeat goes quiet for a tab that is still open, and an unload beacon is lost
whenever the browser is killed. Any version of it is a timeout, and a timeout
is a guess about which attempts are "really" open. What can be observed
reliably is a tab coming to the front, and that turns out to answer the
question rather than raise it.

**A column on `attempts`** — `last_opened_at`, and current is the newest among
the open ones. It would fall back gracefully when the current attempt is
finished. Rejected for that reason as much as for the mechanics: the fallback is
an inference about an attempt the solver has said nothing about, and a column
`save` does not write is one the mappers do not know exists, while one it does
write is rewritten with the whole event log on every mark, racing the command
being recorded.

**An explicit control** — a "this is the one I am asking about" button, or a
`practice focus <id>`. No request nobody asked for, and no ambiguity at all.
Rejected because the complaint was friction, and this trades a question from
the tutor for a button to remember. `practice resume <id>` already is that
command for anyone who wants one.

**Let a finished attempt's page take the mark**, so that going back to a
verdict in another tab makes it current again. Not done: a verdict page left in
a tab would take the mark from the attempt being worked on every time it was
glanced at. A finished attempt keeps the mark it had and cannot take a new one.

## Revisit if

- **Cost 4 or cost 5 is reported**: a tutor shown the tab that was glanced at,
  or yesterday's verdict. Then the mark needs a notion of time — when it was
  made, or how long the page was in front — and the server should say which
  attempt it picked when it is not obvious.
- **Somebody wants a post-mortem on an attempt that never held the mark** and
  expects not to need its id. Then a finished page should be able to take it,
  and the rule needed is the one the last alternative lacks.
- **A fourth surface puts an attempt in front of somebody and forgets to
  mark** (cost 8). Once is a bug; twice is the evidence that the call belongs
  somewhere all of them pass through.
- **A second thing wants to know what is on screen.** One id in one table is a
  mark; two consumers with different ideas of "current" is a session, and
  should be designed as one.
- **A workbench that works without JavaScript appears.** The page's report is
  the first thing it would lose.
