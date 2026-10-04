# 0019 — SQL drills as a third exercise kind

- **Status:** accepted
- **Date:** 2026-10-04
- **Phase:** 14

## Context

`domain/exercise.py` has claimed since Phase 1 that **adding an exercise kind is
an addition**: `Exercise` holds a discriminated `spec` union rather than being
subclassed per kind, "so adding a third kind means adding a spec and a registry
entry instead of re-cutting a class hierarchy". `application/registry.py` kept a
`_PENDING` mapping deliberately empty against the same day, so that a kind
arriving before its grader would produce a readable refusal rather than an
`AttributeError`. PLAN.md §11's stretch menu parked "SQL drills against seeded
SQLite" as a candidate.

That is a prediction with two halves and no evidence. Two kinds is the number at
which a discriminated union and an inheritance hierarchy are indistinguishable:
every `isinstance` is a boolean, every `else` is the other case, and nothing has
yet had to distinguish *this kind* from *the property I am actually asking
about*. [ADR 0008](0008-sm2-first-with-fsrs-behind-a-port.md) and
[ADR 0018](0018-fsrs-as-a-second-scheduler-not-a-replacement.md) established the
shape worth repeating — defer with a stated prediction, then grade it — and the
kind registry was the only other place in the project carrying one.

The constraint that makes SQL the right third kind rather than a second-best
one: it has to be **offline, deterministic and cross-platform**, because PLAN.md
§2 forbids a network and CI runs on Linux and Windows. `sqlite3` is in the
standard library, has a stable query planner, and needs no service. The
alternatives on §11's menu that would have tested the same claim — shell drills,
an embedded terminal, a Docker provisioner — each need something the project has
decided not to depend on.

And it is the kind that applies the project's own thesis to a second domain. The
core bet is *grade the end state, not the answer text*. For a `SELECT` that is
nearly free, because the rows **are** the end state; it only becomes a claim
worth testing for an `UPDATE` or a `DELETE`, which return nothing at all.

## Decision

**Ship SQL drills as a third exercise kind, with their own check vocabulary over
their own read-only port, and change the five things that had learnt to equate
"is a kata" with "has a file to edit".**

Concretely:

- `ExerciseKind.SQL_DRILL` and `SqlDrillSpec` — a seed, a stub, a reference,
  declarative checks and counter-examples. No `allowed_commands` and no command
  budget, because a drill has no console.
- `DrillQuery`, a read-only port in `domain/ports.py` beside `RepoQuery`, with
  `ResultSet` as its vocabulary. Two implementations: `SqliteDrillQuery` and
  `FakeDrillQuery`.
- `domain/drills/` — ten pure assertions in three families: `rows.py` (what the
  answer returned), `tables.py` (what the database was left holding), `craft.py`
  (how it got there: the SQL text, and SQLite's query plan).
- **Two check registries, deliberately disjoint**, rather than one keyed by
  name. The content schema therefore rejects `assert: tree_equals` inside a
  `drill:` block, instead of letting it reach a dispatcher holding the wrong
  port.
- `adapters/sql/` — the engine, built on an **in-memory** database seeded from
  `seed.sql` on every grading pass, with SQLite's own `set_authorizer` denying
  `ATTACH`, a progress-handler deadline, and `sqlite3.complete_statement` for
  statement splitting.
- `EditableSource` and `editable_source()` in the domain — one total function
  answering *is this kind solved by editing a file, and what file*, replacing
  five `isinstance(spec, KataSpec)` tests that each meant that and asked
  something else.

## Consequences

**The inheritance half of the prediction held exactly.** `SqlDrillSpec` is a
dataclass beside the other two. Nothing was subclassed, no class was re-cut,
`build_services` did not change at all, and `build_graders` gained three lines of
which two are a comment. No port was widened, no use case was rewired, and
`domain/checks/`, `adapters/git/`, `adapters/kata/` and every grader but the new
one are untouched.

**The "and a registry entry" half did not hold, and the cost was concentrated in
one place rather than spread.** Five call sites asked whether an exercise was a
kata and meant whether it had a file to edit: the workbench editor seed, the
solution-file handoff, `practice solve`'s next-step line, the fallback source it
reads without `--source`, and the template branch that picks a console over a
CodeMirror pane. For exactly two kinds those questions have the same answer, so
nothing was wrong until a third kind made them different. Naming the question
once costs one dataclass and one function, and is total over the union — so a
fourth kind is a clause mypy demands rather than a branch somebody remembers.

**`_PENDING` turned out to be unreachable by construction, and is deleted.** It
was kept for a kind that exists before its grader does;
`test_every_exercise_kind_has_a_grader` has forbidden exactly that state since
Phase 5. Phase 14 is the first time anything tried to use the mechanism and found
the suite already rules it out. §13's rule — an abstraction nothing has had to
satisfy has not been shown to work — applied rather than quoted, the same way
Phase 11 deleted two check functions. The cost is that the kind had to land in
one large commit with its grader, which is the honest consequence of the
stronger invariant and worth less than the invariant.

**One architecture rule changed, and it was a clarification rather than a
weakening.** `test_only_the_persistence_adapter_speaks_sqlite` becomes
`test_only_the_two_named_packages_speak_sqlite`. The original argument was about
*storage* — one schema, one set of migrations, one transaction boundary, behind
the repository ports — and with one database in the project, "storage" and
"imports `sqlite3`" were the same thing. `adapters/sql/` keeps no schema, no
migrations and no file, and never touches the application's database. The cost of
admitting it is that the rule is now a list with a reason per entry, so two more
tests exist to stop the list rotting: one requires every named package to
actually import `sqlite3`, and
`test_the_drill_engine_does_not_reach_the_applications_database` asserts the
claim the second entry rests on.

**Re-grading had to be made idempotent, which the other two kinds got for
free.** [ADR 0013](0013-grade-on-save-is-a-preview.md) grades on
every Ctrl+S, so an answer runs tens of times. `INSERT INTO orders ...` against a
persistent database gives a different verdict the second time, and
`UPDATE totals SET total = total * 2` a different one every time. pytest against
a file is naturally idempotent and a git fixture rebuilds its repository, so
nothing in the project had had to think about this. The in-memory database is the
fix and it pays for itself twice over: nothing to confine, nothing to clean up,
and `seed.sql` stays readable on disk — which matters, because the solver is
*meant* to read the schema.

**The cost nobody predicted was in the vendored assets.** `vendor.py` claimed a
second language was "a second line here and nothing else". The second line is
right; `workbench.html` had `codemirror-python.min.js` written into its script
tag, so a drill would have loaded a Python tokenizer and then asked CodeMirror
for a `sql` mode it had not loaded — failing by silently degrading to a plain
textarea. No existing assertion could have caught it, because the mode *name*
was already coming from the spec. `vendor.mode_file` makes the mode-to-file map a
fact about the manifest rather than a path a template guesses at.

**What it buys as a product.** Eight drills, five of them exercising assertions
that only exist because the engine reads the database rather than the result set.
`query_plan_matches` is the one the kind is worth having for: two answers
returning identical rows can differ by any factor in work done, SQLite says
which is which in a form stable enough to assert on, and the resulting
`PASS_WITH_ADVISORIES` is §4.4's mechanism carrying the single most transferable
thing in the track.

## Alternatives considered

**One check registry with a family column, instead of two disjoint
vocabularies.** The closest to winning, and rejected on a single failure mode: a
registry keyed by name alone validates `assert: tree_equals` inside a
`sql_drill`, and the check then reaches a dispatcher holding a `DrillQuery` where
it wanted a `RepoQuery`. That is an exercise that cannot grade, discovered at
grading time rather than at build time. Two tables make the vocabularies disjoint
by construction, and the schema rejects the file naming the family. The cost is a
near-twin module and one split model, which is cheaper than the failure.

What the two registries do share is everything that is not a vocabulary —
`CheckSpec`, `CheckResult`, `CheckReport`, `Params`, `compare`, `matcher`,
`suggest_from`, and the three jobs the dispatcher does. That the *shape* of an
assertion did not change when its subject did is better evidence that §6.3's
"negation is a modifier, not a set of paired opposites" was right than the
original argument for it.

**Generalise `CheckContext` to carry either port.** Rejected because it is a
change to working, correctness-critical code in service of a kind that does not
exist yet, and it makes every one of the 20 git assertions take a context that
might not hold a repository. The cost would be paid by the code with the most
coverage and the least reason to change.

**Grade a drill on the text of its SQL.** Rejected by
[ADR 0003](0003-declarative-assertions-over-string-matching.md) before this phase
began, and worth restating because a SQL exercise is where the temptation is
strongest: "did they write JOIN" is so easy to check. It would fail every correct
answer spelled differently, which is the one thing a grading engine must not do —
a solver cannot tell "my SQL is wrong" from "the grader is wrong". `sql_matches`
exists and is **advisory by convention**, enforced over the library by
`test_every_craft_check_is_advisory` rather than trusted to each author, with a
second guard in `practice validate` for an exercise whose only *required* check
reads the text.

**Regular expressions over the answer to block `ATTACH`.** Rejected after
writing out the spellings that defeat one: `ATTACH/**/DATABASE`,
`attach\n  database`, mixed case. A pattern strict enough to catch them starts
refusing `SELECT 'ATTACH DATABASE' AS note`, which is a correct answer.
`set_authorizer` is SQLite's own hook, runs during statement preparation, and
cannot be spelled around — the same argument ADR 0003 makes about grading,
applied to policy.

**A `SqlDrillRunner` protocol between the grader and the engine**, mirroring
`KataRunner`. Rejected under §13: `KataRunner` exists because a pytest subprocess
costs ten seconds and the grader's *mapping* had to be testable without one. A
drill runs in under a millisecond, so the grader is tested against the real
engine and a protocol here would forward one call unchanged.

**A database file in the workspace instead of `:memory:`.** Rejected once
re-grading was thought through — see Consequences. It would also have put a
fourth file type in the workspace, needed a `.gitattributes` binary rule, and
risked the Windows file-locking papercut `sandbox/workspace.py` already absorbs
once.

**A fifth customer in the shared seed**, so that `the-three-biggest-spenders`
could keep its name once the content suite found `LIMIT 3` was vacuous on three
spenders. Rejected in favour of asking for two: one seed across the track is
worth more than one drill's title, and "a `LIMIT` needs more groups than it
cuts" is now the drill's second lesson rather than the accident that hid its
first.

## Revisit if

- **A fourth exercise kind is proposed.** `editable_source` is the thing to look
  at first: if the fourth kind is also file-based, it is one clause; if it is
  not, the question is whether `EditableSource` is still the right shape or
  whether the union has earned a per-kind capability record. The other thing to
  look at is `start-here`, which is now exactly six exercises against a six-row
  dashboard queue and has no slack left.
- **A drill wants data too large to write out as literal rows.** The assertions
  compare against literals in `with:`, which is right for tens of rows and wrong
  for hundreds. The answer is an `expected:` sibling file, and it is a real
  change — the domain would need the file's contents without holding a path, so
  the grader would have to read it and hand it over, which widens the port.
- **The ten assertions stop being ten.** Every one is named by at least one
  shipped drill and `test_every_drill_assertion_is_used_by_some_drill` enforces
  it. An eleventh should arrive with the exercise that wants it; one that stops
  being used should go, as `reflog_contains` and `command_count` did.
- **Someone wants a second SQL dialect.** This is where the decision would
  genuinely hurt: `query_plan_matches` asserts on SQLite's plan output, and
  nothing about `SCAN` or `SEARCH ... USING INDEX` transfers to Postgres. The
  nine other assertions do transfer. A Postgres drill is a different kind with a
  different craft family, not a parameter on this one.
