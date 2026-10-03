# 0012 — The repo state panel reads through the grading port, not a second git path

- **Status:** accepted
- **Date:** 2026-10-02
- **Phase:** 8

## Context

[ADR 0003](0003-grade-git-exercises-by-repo-state.md) commits the project to
grading the end state of a real repository, and PLAN.md §6.2 makes that testable
by putting a **`RepoQuery` port** between the 22 assertion functions and `git`.
Every check is a pure function over that port; `GitRepoQuery` satisfies it by
running git with machine-readable output formats, and `FakeRepoQuery` satisfies it
from an in-memory DAG.

Phase 8 adds the piece PLAN.md §8.4 calls *"the piece that makes git scenarios
teachable"*: a panel showing HEAD and whether it is detached, local and
remote-tracking branches, a `status` summary, the stash, and a commit graph —
redrawn after every command the solver runs.

That panel has to read a repository, and there are two places the reading can come
from. The obvious one is a **new, display-oriented wrapper**: `git status` the way
humans see it, `git branch -vv`, `git log --graph --oneline --all`, parsed loosely
or even passed through as text. It is less code, it needs no new port, and git's
human output is already shaped for a human to read.

The problem is what it makes possible. The panel's purpose is to be read *while
deciding whether to submit*. The verdict that follows is derived from
`RepoQuery`. Two readers of one repository, written at different times against
different git invocations, will eventually disagree — and the disagreement that
matters most is the one that is hardest to notice:

- `worktree_clean` ignores untracked files by default (§6.5), because a scratch
  file someone made while looking around should not fail them. A panel built on
  `git status --short` shows `?? scratch.txt` and reads as dirty. The solver
  cleans up something that was never a problem, or distrusts the verdict that
  calls it clean.
- `head_detached` is answered by `symbolic-ref`, because a detached HEAD sitting
  on a branch tip is still detached. A panel comparing `rev-parse HEAD` against
  the branch refs would call that state attached, correctly-looking and wrong, in
  exactly the exercise where it matters.

When the panel and the grader disagree, the solver has no way to tell which one
lied. That is worse than having no panel.

## Decision

**Repository inspection for display goes through the same `RepoQuery` the grader
goes through.** Concretely:

1. `RepoQueryFactory` — previously a `Protocol` declared inside
   `adapters/git/grader.py`, where the grader was its only caller — **moves to
   `domain/ports.py`**. A protocol in an adapter is reachable only by that
   adapter's collaborators, which was true right up until it was not.
2. `Services` holds **exactly one** factory. `build_graders` is handed it rather
   than falling back to the grader's own default, so there is one place in the
   program that names `GitRepoQuery`, and
   `test_the_grader_and_the_panel_share_one_repo_query_factory` asserts the
   identity.
3. A new application use case, `InspectRepository`, builds **one query per
   request** and returns a `RepoView`. It groups what the port deliberately does
   not — `refs()` answers with one flat map of full ref names, because
   `branch_exists {name: main}` and `tag_exists {name: main}` have to be able to
   disagree — and shortens names only at the point of display.
4. The commit graph is laid out by a **pure function in `application/graph.py`**
   over the `CommitInfo` values `RepoQuery.log` already returns, and rendered as
   inline SVG in the web layer. Nothing in either module asks git anything.

The factory is a *call*, not a stored instance, and that is load-bearing:
`GitRepoQuery` caches every answer for the life of an instance, which is what makes
six questions cost one `git` process. An instance held across a solver's commands
would answer the panel with the repository as it was **before** the command that
prompted the redraw.

## Consequences

**What this buys.**

- The panel and the verdict cannot disagree about the repository, because they are
  the same reading of it. "Untracked only, so this counts as clean" is a sentence
  the panel can print *because* it is the rule the grader applies.
- The panel is unit-testable with no git installed. `BuilderRepoQueryFactory`
  hands back `FakeRepoQuery`, so every state the panel renders — detached HEAD, an
  unborn branch, a four-way dirty worktree, a commit stranded by `reset --hard` —
  is arranged in three lines and asserted in milliseconds.
- `RepoQuery` gains a second consumer, which is the §13 test of whether a port was
  worth having. It was built for grading; it turned out to be the repository's
  read interface.

**What it costs.**

- **Process count.** The panel asks seven questions and redraws after every
  command, and the graph asks one `git log` per distinct ref tip. On a three-commit
  fixture with `main` and `origin/main` on the same commit that is one log; after a
  `reset` it is two. A redraw is on the order of ten `git` processes, which on
  Windows is the slowest thing in the system. Acceptable for a single-user local
  tool driven by a human typing, and it would not be for anything else.
- **The port must stay display-adequate.** `RepoQuery` was designed for
  assertions, and every future display need is now a question about whether to
  widen it. Phase 8 already felt this: the graph would read better with commit
  dates, and `CommitInfo` has none. It was left alone — ordering is done by
  reachability and input position instead — rather than adding a field to a port
  value object for one renderer.
- **One more field on `Services`**, and one more thing a test wiring has to supply.

## Alternatives considered

**A display-only git wrapper.** The closest to winning, and rejected for the whole
of the Context section: it is less code and it reintroduces exactly the class of
silent disagreement the port was built to remove. The cost it avoids — process
count — is one a local single-user tool can afford.

**Cache a repo-state projection on the attempt, updated after each command.** This
would make a redraw free and would be the right answer for a multi-user service.
Rejected because the cache has to be invalidated by *something*, and the only
honest invalidator is "a command ran" — which is every command, so the cache never
hits. It also adds a second source of truth about a repository the solver can edit
from a terminal at the same time (`practice resume <id> --commands` writes into the
same workspace), and the stale panel would be indistinguishable from a correct one.

**Keep `RepoQueryFactory` in `adapters/git/` and let the use case import it.** An
application module importing an adapter is the violation
`tests/unit/test_architecture.py` exists to catch, and suppressing it for one
protocol would have been the first exception in a rule whose value is that it has
none.

**Put the graph layout in `domain/`.** Rejected on the line the domain is defined
by: `domain/` holds what the product can be right or wrong *about*, and a lane
number is not a rule about exercises or grading. `application/` keeps it inside the
coverage gate, which is what the index arithmetic actually needed.

**Render the graph with a library.** Ruled out upstream by PLAN.md §8.2: offline,
no CDN, no npm. §8.4 had already settled on hand-rolled inline SVG generated in
Python, and this is its first use.

## Revisit if

- The redraw becomes slow enough to be felt — a fixture with a deep history, or a
  Phase 11 scenario with many refs. The first thing to try is asking for the graph
  less often than the rest of the panel, not a second git path.
- A display need arrives that `RepoQuery` genuinely cannot serve without becoming
  a worse port for the assertions — commit dates and authors are the likely ones.
  At that point the honest move is a second port over the same workspace, with
  this ADR superseded and the disagreement risk stated again rather than forgotten.
- The web app stops being single-user and local, which would make a per-request
  fan-out of `git` processes indefensible and the cached projection correct.
