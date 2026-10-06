# 0024 — An MCP server over stdio that can only read, built on the SDK as an optional extra

- **Status:** accepted
- **Date:** 2026-10-06
- **Phase:** Phase 19

## Context

Phase 18 turned an attempt into text to paste into a chat
([ADR 0023](0023-the-tutor-context-is-what-the-solver-has-seen.md)). The paste
has one flaw that no amount of care removes: it is a snapshot, stale the moment
the solver runs another command. The second half of the original request was
"is there a more advanced way to do this", and the answer is the Model Context
Protocol: a client such as Claude Desktop or Claude Code starts a local server
and calls tools on it, so the model fetches the attempt itself, as often as it
likes.

Four things were true going in.

**The read side already existed.** `ExportTutorContext` decides what a tutor may
be told, with the spoiler boundary held in a type. A server is a third surface
over it, not a new feature.

**`RepoQuery` is read-only by design.** Every method on it is a question
(§6.2). That is what made twenty assertions unit-testable, and it is also the
shape a tutor's access wants.

**The attempt's log is evidence.** Advisory checks (§6.3) and the grade
suggestion read it to judge how the solver got there. Anything that writes to
it on a model's behalf is graded as the solver's own doing.

**The project installs nothing that can phone home**, and says so in
`pyproject.toml` and PLAN.md §2. The official SDK carries an HTTP client, an
auth stack and `cryptography`.

One more arrived during the phase and changed the design of the second use
case: **the caller is a model choosing its own arguments.** Every other use
case is handed input a solver typed or a template built.

## Decision

**`practice mcp` runs an MCP server on stdio, exposing three tools and one
prompt, all of which read.** `list_attempts`, `get_context` and `read_file` are
backed by `ListOpenAttempts`, `ExportTutorContext` and a new `ReadAttemptFile`.
None of those holds a clock, a grader or a route to `Workspace.run`, so the
server cannot change an attempt because there is nothing on `Services` it could
call that would. Each tool carries the protocol's read-only annotation.

**No tool runs a command.**

**`ReadAttemptFile` reaches a repository only through `RepoQuery`**, and treats
the path and the revision as untrusted input. A revision beginning with `-` is
refused, and what reaches `read_blob` is the hash `rev_parse` resolved, never
the caller's string. For a kata or a drill the only readable files are the one
the solver edits and a drill's `seed.sql`; the hidden suite is refused by name.

**The server is built on the official `mcp` SDK, installed as an optional
extra.** `uv sync --extra mcp` opts in; the base dependency set is unchanged.
`practice.interface.mcp` is the only package that imports it, held by
`tests/unit/test_architecture.py`, and `practice mcp` defers that import and
turns a missing SDK into an instruction.

**stdio is the only transport.**

**The spoiler boundary and the interview refusal are inherited from the use
cases**, not restated in the adapter.

## Consequences

**What this buys.** A tutor whose picture of the attempt is current: two
processes, one database, and each tool call reads again
(`tests/e2e/test_ask_a_tutor_over_mcp.py` runs a command in one and sees it
from the other). It can look at a conflicted file or at what a file held at
`origin/main` without the solver pasting anything. And it is a third test of
PLAN.md §2's claim about driving adapters, after the CLI: a protocol with no
HTML in it serves the same use cases the web app does, and nothing under
`application/` or `domain/` had to learn that it exists.

**What it costs.**

1. **Thirteen packages**, for anyone who opts in, and `uv.lock` grows by them.
   No existing pin moved. The base install is exactly what it was, which is the
   point of the extra, but the dev group has to carry the SDK too or CI cannot
   import it.
2. **The SDK's API moved under the plan.** The plan assumed the 1.x API; the
   installed 2.3 had renamed the server class and changed the client. Every
   line here was written from the installed package. A dependency whose major
   version turns over in the time it takes to plan a phase is a maintenance
   cost this project did not have before.
3. **"Read-only port" turned out to be a claim about a contract, not about an
   implementation.** `GitRepoQuery.read_blob` runs `git show <rev>:<path>`, and
   `git show --output=FILE` opens FILE for writing. Every revision it had ever
   been handed came from an exercise author. Checked against real git before
   being written down. The guard is in the use case, the one untrusted caller;
   **the adapter is unchanged**, so the hazard is still there for the next
   caller who passes it a revision from somewhere new.
4. **Asking a tutor is still invisible to the grade suggestion.** ADR 0023
   accepted this for a copied bundle on the grounds that the tool cannot know
   it was pasted. That argument does not hold here — a tool call is something
   the application can vouch for — and the hole is left open anyway, because
   recording it means a write on the read path. It is the first thing under
   **Revisit if**.
5. **A weaker tutor than a model with a shell.** It can look and cannot try
   things, so "run `git status` and tell me" is still a round trip through the
   solver. That is the feature, and it will sometimes feel like a limitation.
6. **The SDK logs every refused tool call to stderr.** Harmless to the protocol
   and noisy in a client's log.

## Alternatives considered

**Hand-roll the protocol: a few hundred lines of JSON-RPC over stdio, standard
library only.** The closest to winning, and what this project's own habits
point at — HTMX and CodeMirror are vendored files, not packages, for the reason
that would apply here. It would have kept the dependency set and the lockfile
untouched and needed no extra, and it was the recommendation going in. The
project's owner chose the SDK instead, on the grounds that owning a wire format
is a standing cost — every protocol revision becomes this project's to track —
where the extra is a one-time one. The decision is recorded as taken, with the
note that cost 2 above is the same drift arriving through a different door.

**A fourth tool that runs allowlisted commands through `RunScenarioCommand`.**
The better tutor, again. Rejected because the command would land in the
solver's log and count against their budget, so the advisory checks and the
grade suggestion would be judging a person on a program's choices — and a
"dry-run" variant that did not record would be a second execution path with
neither of the sandbox's two properties (§8.1).

**"Read-only" git commands, vetted by the command policy.** The first sketch of
`read_file`. Rejected because whether `git branch` reads or writes depends on
its arguments, so the classification would be a second, worse copy of git's
option parser. `RepoQuery` is already the list of questions that are safe to
ask.

**The SDK as a base dependency.** Simpler: no extra, no deferred import, no
refusal to test. Rejected because "nothing here may phone home" is a claim
about what is installed, and a solver who never asks an AI anything should not
be installing an HTTP client to support a feature they do not use.

**An HTTP transport**, which the SDK provides. Rejected because a listening
port needs the whole of `interface/web/security.py` — loopback binding, the
origin guard, the `Host` check — argued over again for a second server, to
reach a client that is already on the same machine and can spawn a process.

**Harden `GitRepoQuery.read_blob` instead of guarding the use case**, with
`--end-of-options`, which real git accepts and which refuses the injection.
Rejected for now because it changes the path every `file_at_ref_matches` check
is graded through, in a phase whose claim is that nothing under `adapters/`
moved. It is the right fix and it should be its own change, with the
conformance suite run over it.

**Restate the spoiler boundary in the adapter**, filtering the context before
it is returned. Rejected as the way a fourth surface comes to disagree with the
other three. The adapter renders what the use case built and refuses what it
refuses.

**Guess when several attempts are open** — the newest, say. Rejected because a
tutor confidently describing the wrong repository is the failure this feature
exists to prevent. It refuses and lists the ids, which costs one round trip.

## Revisit if

- **A solver passes with the tutor's help and is scheduled as though they had
  not.** Over MCP the application knows a tutor was consulted. Recording a
  `TutorConsulted` event would make `get_context` a write, so it should arrive
  as its own decision with the migration it needs, not as a side effect here.
- **`read_blob` gains a second caller that passes a revision it did not
  write.** Then the guard belongs in the adapter, and `--end-of-options` is
  the change.
- **The SDK's major version turns over again.** One rename is a cost; a habit
  of them is the evidence the hand-rolled alternative was missing, and the
  server is small enough — three tools — that the swap is contained to one
  module.
- **Somebody wants the tutor to run something.** The condition is a way to do
  it that does not put a program's commands in a person's log: a separate
  scratch clone of the workspace would qualify, and is a `SandboxProvisioner`
  question rather than an MCP one.
- **A client appears that cannot spawn a process**, which is the one thing
  that would justify the HTTP transport and the security work that comes with
  it.
