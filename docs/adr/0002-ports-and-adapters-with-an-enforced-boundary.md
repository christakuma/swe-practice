# 0002 — Ports and adapters, with the boundary enforced by a test

- **Status:** accepted
- **Date:** 2026-09-30
- **Phase:** 0

## Context

The correctness-critical part of this system is small and pure: the ~25
assertions that decide whether a repo ended up in the right state, the attempt
lifecycle invariants, and the SM-2 scheduling arithmetic. Everything around it is
I/O and nothing but I/O — subprocess calls to git, SQLite, the filesystem, HTTP.

Those two halves want opposite things. The pure half wants tests that run in
milliseconds and can enumerate edge cases exhaustively. The I/O half needs real
git in real temporary directories, which is slow and platform-dependent — and
Windows is the primary dev machine (PLAN.md §13), so "slow and
platform-dependent" is not hypothetical.

If the assertions reach for `subprocess` directly, every one of the ~25 needs a
real repo built to test it, and the suite that should take milliseconds takes
minutes. There is also a second driving adapter in the plan — a Typer CLI
alongside the web app — which only works if the use cases are genuinely
independent of HTTP.

And there is a failure mode specific to this style: a project claims hexagonal
architecture in its README, then someone imports a concrete adapter into a use
case because it is 3pm and it works. Nothing fails. The claim quietly becomes
false, and the next reader cannot tell which parts of the boundary are real.

## Decision

Ports and adapters, dependencies pointing inward:
`interface/ → application/ → domain/ ← adapters/`.

- `domain/` is pure: no `subprocess`, no `sqlite3`, no filesystem writes, no
  HTTP. Data and functions.
- Ports are `typing.Protocol` definitions declared in `domain/ports.py` —
  structural, so adapters implement them without importing them and without an
  inheritance relationship pointing the wrong way.
- The ~25 check functions live in `domain/checks/`, as pure functions over the
  `RepoQuery` port rather than over a git process.
- `composition.py` is the only module permitted to import across all layers.
  Manual dependency injection, no framework.
- **`tests/unit/test_architecture.py` AST-walks every module under `domain/` and
  `application/` and fails the build on any import from `adapters/` or
  `interface/`.** Part of the same phase as the boundary itself, not a later
  addition.
- A Typer CLI is built as a second driving adapter over the same use cases.

## Consequences

- The ~25 assertions are tested against a `FakeRepoQuery` with no git involved,
  so the pure suite stays in milliseconds. A separate conformance suite asserts
  `GitRepoQuery` and `FakeRepoQuery` agree — without it, fakes drift and the fast
  tests become fiction.
- Because the checks are in `domain/`, they fall inside the 90% coverage gate on
  `domain/` and `application/`. That was the explicit reason for moving them
  there (PLAN.md §16): they had been placed under `adapters/`, which put the most
  correctness-critical code in the project outside the gate.
- The CLI is a load-bearing test of the boundary, not a convenience. If the core
  were secretly coupled to HTTP, a second driving adapter would not work — and it
  makes end-to-end tests cheap and keeps `practice validate` runnable in CI with
  no server.
- Cost, stated plainly: more indirection than a 3,000-line program needs, and a
  port with exactly one real implementation looks like ceremony until the second
  one arrives. `RepoQuery` earns it immediately (two implementations from day
  one); some others will not.
- Manual DI means `composition.py` grows and every dependency is passed by hand.
  Accepted deliberately: the whole object graph stays readable in one file.

## Alternatives considered

- **A conventional layered app** (`models/`, `services/`, `db/`) with the pure
  logic merely "kept tidy" by discipline. Rejected for the reason in the Context:
  discipline is unobservable. The AST test costs an hour and converts an
  aspiration into a build failure.
- **Ports as ABCs instead of Protocols.** Forces adapters to import the domain to
  subclass it — which is the correct direction for dependencies, so this was
  close. Protocols win on testability: a fake needs no base class, and a
  `FakeClock` stays five lines.
- **A DI container.** Solves a problem this project does not have. Manual wiring
  in one readable file beats magic at this scale.
- **Checks in `adapters/`, next to the git code.** This was the first draft, and
  it was wrong twice over: it coupled pure assertions to a subprocess
  implementation, and it excluded them from the coverage gate.
- **Skipping the CLI.** Would have saved ~200 lines and removed the only
  independent evidence that the application layer is actually decoupled.

## Revisit if

The architecture test starts needing an allowlist of exceptions. One exception is
a mistake to fix; a list of them means the boundary is in the wrong place, and
the honest response is a superseding ADR rather than a growing set of ignores.

## Note — 2026-09-30 (Phase 0)

Order of work worth recording: `domain/` and `application/` were created as empty
packages in the scaffold commit, before any code, so the coverage gate measures
the right two directories from the first commit. A gate added after the code
exists gets its threshold tuned to whatever the code already scores.

## Note — 2026-09-30 (Phase 1)

The boundary test now exists, and two things about building it are worth recording
because they are the difference between an enforced boundary and a decorative one.

**The detector is tested against deliberate violations.** Fourteen cases build a
module tree that breaks each rule and assert the walk reports it; seven more
assert it stays quiet about what the domain legitimately needs. An architecture
test whose detector is broken passes exactly as happily as one whose architecture
is sound, and nothing else in the suite can tell the difference.

**Relative imports are resolved to absolute names, not prefix-matched as text.**
`from ...adapters.git import GitRepoQuery` otherwise reads as a target of
`adapters.git` and walks straight past a `practice.adapters` prefix check — and a
relative import is exactly the spelling someone reaching for a shortcut writes.
Resolution has to know which modules are packages, since a package resolves `.`
against itself and a module against its parent. The walk covers whole files rather
than module-level statements, so a deferred import inside a function is caught too.

The test also asserts that the walk **found** the modules it claims to police. A
wrong root path or a glob that matched nothing would otherwise leave the whole
file green forever while checking nothing at all.

Scope grew slightly beyond the decision as written: `domain/` is additionally
checked for imports of I/O modules — `subprocess`, `sqlite3`, `socket`, `os` and
the rest — because the first consequence listed above is a claim about zero I/O,
not only about layer direction. `pathlib` is deliberately not on that list:
`PurePosixPath` is pure, and a content adapter handing the domain a parsed path is
legitimate.

One consequence landed exactly as predicted: `Clock` and `IdGenerator` got their
second implementations in `tests/fakes/` in the same phase they were declared, and
the conformance check is **mypy**, not `isinstance`. Assigning each fake to a
variable annotated with its port makes `--strict` reject a fake that drifts out of
shape. `runtime_checkable` plus `isinstance` checks that attribute names exist and
not that signatures match, so a `FakeClock` whose `now()` took an argument would
pass it.
