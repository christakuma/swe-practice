# 0015 — Verify on the working tree, not on every commit

- **Status:** accepted
- **Date:** 2026-10-03
- **Phase:** decided in Phase 11 — Content build-out; written up in Phase 12

## A note on the date

This is the one ADR here that was not written the day the decision was made, and
the index says why that is normally a bad idea: a retrofitted ADR keeps the
justification and loses the alternatives. It is written anyway, and it is not a
reconstruction — PLAN.md §11 and §16 recorded the reasoning, the measurements
and the rejected position *at the time*, and this file moves them into the
record where a reader looking for decisions will find them. What it adds is the
alternatives section, which the plan did not have. Where this ADR and §11
disagree about anything, §11 is the contemporaneous text.

## Context

Phases 0 through 10 enforced a rule: **every commit in a phase must be green on
its own.** It was enforced for real, by a loop that checked out each commit of a
phase in turn, ran lint, types and that commit's own test directories against it,
and a second loop that bisected the attribution when the first went red.

The rule sounds unarguable. It stopped being affordable at Phase 11, and the
three things that changed are all consequences of the library growing from 3
exercises to 54:

1. **The per-commit cost became linear in content nobody was testing.** The loop
   is seconds per commit while a commit's tests are fast. The content suite walks
   every exercise, provisions 24 git repositories and runs a `pytest` per kata, so
   it is minutes per commit — and the attribution loop is minutes per commit
   again. Phase 11 spent well over an hour of wall clock on verification runs,
   most of it re-running work that the pre-push suite then ran once more.

2. **The rule could not see a content commit at all.** The loop derived its test
   paths from the test *directories* a commit touched, and a content commit
   touches none. So the rule was already not holding for seven of Phase 11's
   thirteen commits. Claiming it held would have been the worst of both: the cost
   of the loop and none of the guarantee.

3. **Nothing downstream depends on the property.** There is no release process,
   no cherry-picking between branches, and no bisect across a phase boundary. A
   commit that cannot stand alone is discovered the moment anyone checks it out,
   and the fix is a reorder or a squash.

The thing the rule was actually protecting — that `git bisect` works — needs
commits that **build**, far more than it needs every commit to pass every test.
And a bisect over this history would be looking for a regression in the last few
commits, not across a phase that added fifty-one exercises.

## Decision

**The per-commit tier runs on the working tree. There is no `git checkout`
anywhere in the verification process.**

Per commit:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q --no-cov <the tests this change touches>
```

Before a push, once, and this is the tier that decides — it is exactly what CI
runs on both platforms:

```bash
uv run pytest --cov --cov-report=term-missing -n 4 --dist loadfile
```

What survives of the old rule is a weaker claim that is still worth holding:
**a commit list is a dependency order.** A commit whose module imports something
a later commit adds is a commit nobody can read on its own, and narrative order —
foundations first, then the interesting part — is not the same as dependency
order. `mypy` over the working tree checks this for free: it names the missing
import, by line, without running anything.

## Consequences

**What it buys.** Verification is seconds instead of minutes, which is the
difference between a tier that gets run and one that gets skipped. No checkout
means no clean-tree requirement, no editable-install confusion, and no
re-running of commits that were already fine. And the tier now covers content
commits, which the loop structurally could not.

**What it costs.**

- **A commit in the middle of a phase may not pass its own tests.** That is a
  real loss and it is the one being accepted. `git bisect` over such a history
  can land on a commit whose failure is not the failure being hunted.
- **The fast tier cannot see three classes of defect**, and they are documented
  rather than papered over (PLAN.md §11): a second test run competing for temp
  directories and `.coverage` invents failures that do not reproduce; a changed
  user-facing string breaks a test in a directory the change did not touch, which
  only `grep -rn` catches; and a content change is covered only by `-m content`
  and `tests/e2e`.
- **The pre-push run is now load-bearing in a way it was not.** It is the only
  tier that sees the whole suite, so skipping it is skipping verification rather
  than skipping a repeat.

## Alternatives considered

**Keep the rule and make the loop cheaper** — run only the fast markers per
commit, or skip the content suite. The closest to winning, because it keeps the
property. Rejected because it keeps the property *in name*: a loop that skips the
content suite cannot say a content commit is green, which is precisely the case
that broke, and it would have left the rule claiming more than it checked.

**Keep the rule and squash harder** — fewer, larger commits, each green. This
trades the thing the history is for. The commit log is part of what this project
is *for* (PLAN.md §11: "worth doing because it makes the git history itself part
of the portfolio"), and thirteen commits that each say one thing are worth more
here than four that each pass a test loop.

**Enforce it in CI on the pull request instead** — a workflow that checks out
every commit in the branch. Rejected on the same cost, moved somewhere less
visible: it is the same minutes, paid by a runner, discovered after the push, and
on a two-core runner it is worse. It also makes the feedback arrive at the moment
it is most expensive to act on.

**Drop the pre-push gate and keep per-commit greenness.** Considered because it
is the symmetric option and it is strictly worse: the per-commit tier runs each
commit's *own* tests, so nothing would ever run the whole suite, and the
cross-cutting failures above are exactly the ones a per-commit tier cannot see.

## Revisit if

- **Anything starts to depend on a commit standing alone.** A release process,
  cherry-picks between branches, or a bisect that genuinely has to cross a phase
  boundary. Then the property is worth paying for again — but pay for it with a
  CI job on the branch, not with a loop on the developer's machine.
- **The pre-push suite stops being affordable.** It is 7m20s at 54 exercises and
  the content suite is most of it. At 150 exercises it is the tier that needs
  splitting, and the lever is already identified: `--dist loadgroup` with a group
  per `(module, exercise)` balances far better than `loadfile`, which currently
  lets the longest file set the floor for the whole run.
- **A defect ever escapes to `main` that per-commit greenness would have
  caught.** None has; the one that escaped Phase 11 was a library that outgrew
  the dashboard's first screen, which no per-commit loop could have seen either.
