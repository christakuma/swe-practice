# 0007 — HTMX and server-rendered fragments, not a single-page app

- **Status:** accepted
- **Date:** 2026-10-02
- **Phase:** 7

## Context

Six phases built a core that is reached through ports and driven by a Typer CLI.
Phase 7 adds the second driving adapter, and it is the one the product is
actually for: commit graphs, diffs and syntax-highlighted code are genuinely
painful in a terminal.

Five constraints come from decisions already made rather than from taste.

**Offline is a hard requirement, and it rules out a build step by implication.**
PLAN.md §2 and §8.2: no CDN, no network at runtime, everything vendored and
committed. A React or Svelte front end is not merely a dependency — it is an npm
toolchain, a `node_modules`, a bundler and a lockfile in a project whose entire
toolchain is `uv`, for a tool that must work on a laptop with the wifi off. The
build output would also be committed, which means reviewing a diff of minified
JavaScript on every change.

**The server already owns every decision a client would want to re-make.** A
verdict is a `Verdict` of `CheckReport`s with a derived `Outcome` and a
severity-aware notion of what counts as a failure (§4.4). An SPA would need a
TypeScript mirror of that — what a check is, which severities block, how an
outcome is derived — and the two would be free to disagree. The place that
disagreement surfaces is a verdict panel showing something the grader did not say.

**There is no second consumer, and there will not be one.** §1's non-goals rule
out accounts, sync and multiplayer. One user, one machine, one browser tab,
against a server on loopback. A JSON API exists in that world only to be consumed
by the one client shipped beside it.

**Latency is not the constraint people usually optimise against here.** The
server is on `127.0.0.1`; a round trip costs under a millisecond. What a
submission actually costs is a pytest subprocess or a `git` process — hundreds of
milliseconds to seconds — and no client-side rendering strategy changes that.

**The CLI has to keep working, and has to stay a real second adapter.** §2's
claim is that a second driving adapter is the proof the hexagonal boundary is
not decorative. An architecture that moved logic into a browser client would make
the CLI the odd one out and the claim false.

## Decision

The web app is **FastAPI + Jinja2 templates + HTMX**, serving HTML. Mutating
interactions POST and receive an **HTML fragment**, which HTMX swaps into a known
element. There is no JSON API: `openapi_url=None`, and the interactive docs go
with it.

The fragment a submission returns is the **same template** the full page includes
when it renders an already-graded attempt (`partials/verdict.html`). One template
per thing, used from both directions.

JavaScript is written only where the browser is the only thing that knows
something. In this phase that is exactly one place: CodeMirror replaces the
textarea with its own document, so the submission reads `editor.getValue()`
rather than letting HTMX serialise an element that has stopped tracking the
screen.

## Consequences

**What this buys.**

- One model of a verdict, in Python, inside the coverage gate. There is no second
  definition of "failed" to keep in step.
- A page and a fragment that cannot disagree, because they are one file. The test
  that asserts a reload shows exactly what the submission showed is two lines.
- No build step, no `node_modules`, no committed bundle. `uv sync` is the whole
  setup, on both platforms.
- Tests that assert on what the browser actually receives. `TestClient` plus a
  substring is the entire apparatus; there is no component renderer, no jsdom and
  no second test runner.
- The CLI and the web app stay genuinely parallel — both call the same use cases
  and format the result themselves, and `dto.py` carries domain objects precisely
  so neither owns the other's formatting.

**What it costs, and these are real.**

- **Every interaction is a round trip.** Fine on loopback and wrong on a network;
  this design does not survive being deployed, which is also not a thing it is for.
- **Rich client state is awkward.** Anything with genuine client-side state — a
  drag-to-reorder interactive-rebase plan (§15, Q2), a live-filtering list —
  becomes hand-written JavaScript rather than a component. The escape hatch is
  there and it is not free.
- **Template logic is unchecked.** `mypy --strict` covers the routes and stops at
  the `{{ }}`. A renamed DTO attribute is a silent empty string in a page, which
  is why `tests/web/` asserts on rendered substrings rather than on status codes.
- **The HTMX call being hand-written is a sharp edge.** `hx-post` on the form
  would serialise the stale textarea and submit the stub for ever, on a page that
  looks entirely correct. That trap is now documented in the template, which is
  not the same as it being impossible.
- **No offline-capable client.** The page needs the server for everything. Given
  that the server is what runs git and pytest, this costs nothing today.

## Alternatives considered

**React or Svelte with a JSON API.** The one closest to winning, because it is
what the job description of "web app" normally means and because the commit-graph
rendering of Phase 8 is the kind of thing component state suits. Rejected on
§8.2: it brings an npm toolchain into a Python project, and the vendoring rule
would then require committing a bundle nobody can review. It also duplicates the
verdict model in TypeScript, which is the specific failure this project has spent
six phases arranging not to have.

**Alpine.js instead of HTMX.** Also single-file and vendorable, so the offline
objection does not apply. Rejected because it is a *client state* library and the
state here lives on the server: an attempt is a row in SQLite and a directory on
disk, and the browser's correct opinion about it is none. HTMX's model — the
server owns the HTML, the client swaps it — matches what is true.

**Plain forms and full page reloads, no JavaScript at all.** Genuinely tempting,
and it survives every constraint above. Rejected for Phase 8 rather than for this
one: a command console that reloads the page after every `git status` loses the
scroll position and the transcript, and the repo state panel is meant to visibly
change beside the console. Choosing it here would mean changing the decision one
phase later, with templates written for it.

**Server-sent events or WebSockets for the command console.** Deferred, not
rejected. Nothing in Phase 7 or 8 streams: a command runs to completion under a
timeout and then renders. If an exercise ever needs live output from a
long-running process, this is where to look first.

## Revisit if

- A second consumer appears that is not a browser — a VS Code extension, a mobile
  client, anything that genuinely needs JSON. A JSON API added for one real
  consumer is a different decision from one added speculatively.
- A page needs client state that hand-written JavaScript can no longer hold
  honestly. The interactive-rebase plan editor of §15 Q2 is the known candidate;
  if a second lands beside it, the balance has moved.
- The app is ever meant to run somewhere other than loopback, at which point the
  round-trip cost stops being free and most of this reasoning changes with it.
