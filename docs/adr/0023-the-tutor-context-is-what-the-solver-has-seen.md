# 0023 — The tutor context is a projection of what the solver has already seen

- **Status:** accepted
- **Date:** 2026-10-06
- **Phase:** Phase 18

## Context

The request was *"an easy way to ask an AI questions about the scenario"*, with
a first sketch attached: a JSON file that tracks what you do as you go, carrying
a prompt that makes the model a tutor, to paste into a chat box.

Three things were already true that shaped the answer.

**The tracking exists.** `Attempt` has kept a full event log since Phase 1 —
every command with its exit code and output, every hint with its index — because
the process assertions (§6.3) and the grade suggestion read it. `InspectRepository`
(ADR 0012) reads the live repository through the port the grader reads through.
So the thing to be pasted is a *reading* of state the application owns, and a
second log written alongside the first would be two records of one attempt.

**An `Exercise` is mostly answer.** It holds every hint (the last is usually the
command), the author's notes (the lesson, written out) and, for a scenario or a
drill, a check list whose labels describe the end state one by one. Any code
handed an `Exercise` and asked to describe an attempt is one line away from
printing all of it.

**The reader is a model, by way of a clipboard.** The bundle is plain text the
solver copies by hand and can read on the way. Nothing downstream of the paste
is under this project's control.

One more turned up while building it, and it is worth recording because nobody
went looking: **`exercise.notes` had never been shown anywhere.** 115 exercises
carry a `notes.md`, `practice validate` requires each to be non-empty, and no
template and no command prints one. The post-mortem below is the first surface
that does.

## Decision

**A use case, `ExportTutorContext`, projects one attempt into a `TutorContext`
that holds only what the solver has been shown.** While the attempt is open that
is the task, the event log, a *count* of the hints left, the live repository and
the solver's own source. Hints not yet revealed, the notes and the checks are
not fields on the type. Once a verdict exists, the verdict and the notes are
added, and the same request is a post-mortem.

**The boundary is structural rather than instructed.** `TutorContext` is the one
DTO in `application/dto.py` that does not carry the `Exercise` whole, and the
two renderers in `application/tutor.py` are pure functions over it — so the half
that has to be right about spoilers has no formatting in it, and the half with
all the formatting cannot leak what it was never given. The prompt that asks the
model to tutor rather than answer is real and is sent, but it is not what the
boundary rests on.

**Three surfaces, one text.** A button in the workbench's prompt column,
`practice context`, and (Phase 19) an MCP server all render the same context
through the same function. Markdown by default; `--format json` for a caller
that wants the fields.

**An interview that is still open is refused**, by `AttemptPolicy.offers_tutor`
— the same kind of clause as `reveals_workspace` (ADR 0020), and an affordance
withdrawn rather than a containment for the same reason. A finished interview
is picked over like any other attempt.

**Nothing is recorded.** Exporting writes no event.

## Consequences

**What this buys.** A tutor on all 115 exercises and all three kinds, with no
new port, no adapter touched, no migration and no dependency, and with the app
still making no network call of its own (§8.2): it prepares a paste. The
repository a model is told about is the one the panel shows and the grader will
read, because all three go through `view_of`. And the claim about spoilers is a
test — `tests/content/test_tutor_context.py`, over every exercise on disk —
rather than a hope about a prompt.

**What it costs.**

1. **Asking a tutor is invisible to the grade suggestion.** "Passed, with three
   of four hints" is distinguished from "passed"; "passed, after a model talked
   me through it" is not. This is a real hole in the review scheduling and it
   is accepted, not overlooked — see the second alternative.
2. **The bundle carries whatever the solver's commands printed, and that can
   include a path.** `git push` to the fixture's remote prints
   `C:/Users/<name>/.../remotes/origin.git` on stderr, the log records it, and
   the bundle repeats it into a chat. It is the solver's own transcript and they
   have already seen it, but they did not type it and may not expect to be
   sending it. Not redacted here, because the application layer does not know
   where the workspace is and should not.
3. **The copy button cannot promise it copied.** The asynchronous clipboard API
   rejects in a document that is not focused — found by pressing the button in
   an embedded browser pane — so the handler falls back to `execCommand`, and
   failing that leaves the text selected and says so. Three routes for one
   button is the honest price of a clipboard.
4. **A pipe on Windows is still not quite safe.** `practice context` writes
   UTF-8 bytes itself when it is not on a console, because 96 exercises hold a
   character cp1252 cannot encode and Python's own stdout would have raised.
   That fixes the half this command controls. Windows PowerShell then decodes a
   native command's output in *its* code page before `Set-Clipboard` sees it,
   which is why `--output FILE` exists.
5. **The endpoint is a POST that writes nothing.** A kata's solution lives in
   the browser's editor until it is submitted, so the server has to be sent it.
   Every other read in the app is a GET, and this one is not, for a reason that
   has to be explained wherever it is noticed.
6. **Interview mode withdraws a third affordance**, and its banner had to change
   to say so.

## Alternatives considered

**Hand the model the whole exercise, with a prompt telling it not to reveal the
answer.** The closest to winning, because it would make the better tutor: a
model that knows the fix can steer toward it precisely, and one that does not is
working the problem out alongside the solver. Rejected because the boundary
would then be a request. Models repeat what they were told not to when asked
twice, and the bundle is text the solver reads as they paste it — the answer
would be on their clipboard and on their screen whatever the model did. A tutor
that is sometimes weaker is a better trade than a hint ladder that can be
skipped by pressing a different button.

**Record a consult on the attempt, the way a revealed hint is recorded.** The
principled option, and consistent with the reason hints are recorded at all. It
was rejected on what the tool can honestly claim: it showed a hint, but it only
*copied* a bundle. Whether anything was pasted, into what, and what came back
are all unknown, so the event would mean "pressed a button" and the grade
suggestion would be penalising a click. It would also have cost a new event
type, a migration and a change to `suggest_grade`, and turned a read into a
write. The grade is the solver's own call in the end — `suggest_grade` only
suggests, and `GradeReview` takes whatever grade it is given — and they know
whether they had help.

**A recorder: write the JSON as the solver works.** The original sketch, taken
literally. Rejected because `Attempt.events` is already that record, persisted,
and read by two other features; a file beside it would have to be kept in step
with it and would be wrong whenever it was not.

**A built-in chat panel that calls a model API.** Rejected on §8.2: it needs a
key and a network call, in an app whose test suite greps for external URLs. A
local model keeps the offline claim and trades it for a service dependency and a
worse tutor. Preparing a paste costs the solver one keystroke and keeps the
choice of model theirs.

**JSON as the default format.** What was first asked for. Rejected as the
default because of the reader: a conflicted file's contents inside a JSON string
is a wall of `\n`, and both a chat model and the person checking the paste read
fenced prose more easily. Kept as `--format json`, built from the same context.

**Put the renderer in the web layer, beside the template that shows it.**
Rejected because three driving adapters produce this text, and a rendering owned
by one would be imported sideways by the other two. `application/graph.py`
already made the argument for a view model with no I/O living one layer in, and
it also puts the renderer inside the coverage gate.

**Refuse an open attempt whose workspace has been collected**, as
`InspectRepository` does. Rejected because the history is the larger half of
what a tutor is asked about and it lives in the database: the bundle is still
useful with no repository in it, and says the repository is gone.

## Revisit if

- **Somebody passes with a tutor's help and is rescheduled as though they had
  not**, and notices. That is the evidence the second alternative is missing,
  and Phase 19's MCP server changes the calculation: a tool call *is* an event
  the application can vouch for, where a copy was not.
- **A path in a pasted transcript turns out to matter to someone.** The fix
  belongs in the sandbox, which knows the workspace root and could rewrite it
  in captured output, rather than in a renderer that would be guessing.
- **The tutor turns out to be too weak without the checks.** The middle option —
  labels without explanations — was on the table and declined. It should be
  reopened with examples of the tutor steering wrong, not on a hunch.
- **A second prompt is wanted** — a stricter one, or one per exercise kind.
  `TUTOR_PROMPT` is a constant because there is one; a second makes it content,
  and content belongs in the library (ADR 0004).
