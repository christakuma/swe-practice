# 0003 — Grade git exercises by repo state, not command text

- **Status:** accepted
- **Date:** 2026-09-30
- **Phase:** 0

## Context

The skill this project claims to teach is not recall. Flashcards grade
*recognition*: you read "how do I undo a pushed commit?", flip the card, nod, and
learn nothing transferable. The actual skill is being dropped into a repo that is
already broken and knowing what to look at first.

That gap is the entire reason the project exists, so the grading mechanism has to
be chosen against it rather than for convenience.

The obvious cheap mechanism is to compare what the learner typed against an
expected command. It fails in both directions, and both failures are fatal to the
premise:

- **False negatives.** `git revert HEAD`, `git revert --no-edit HEAD`,
  `git revert <sha>`, and `git revert HEAD~0` are the same correct answer. A
  matcher punishes three of them for not being the string the author happened to
  anticipate. A tool that marks correct answers wrong does not get used twice.
- **False positives, which are worse.** `git reset --hard HEAD~1` followed by
  `git push --force` produces the right *tree*. It is also exactly the mistake
  the exercise about published history exists to teach you not to make. Text
  matching either accepts it or rejects it by name — it cannot say *why* it is
  wrong, because it never looked at the repository.

## Decision

Grade the **end state of a real repository**.

Each git exercise ships a `fixture.sh` that builds a real repo in a throwaway
workspace with a real problem in it — detached HEAD, a bad merge, a commit already
pushed to a shared branch, a forgotten stash. The learner runs real git commands
against it. Grading inspects the resulting repo state through the read-only
`RepoQuery` port and evaluates declarative assertions from the exercise's own
`exercise.yaml`.

No string matching of learner commands anywhere in the grading path. The command
allowlist exists for sandbox safety (PLAN.md §8.1), never as a correctness oracle.

## Consequences

- Any correct route passes, including ones the author did not think of. The tool
  cannot punish an answer it failed to anticipate, because it is not comparing
  answers.
- Feedback becomes nuanced instead of binary. The reset-and-force-push case gets
  graded as: *correct tree, but you rewrote history that was already published —
  here is why that is the wrong tool here.* Expressed as a `required` check the
  solution must satisfy plus advisory checks that name the damage.
- **The fixture is the lesson.** Reading a broken repo is the thing being taught,
  so the artifact that sets up the problem is content, not test plumbing.
- Cost: this is by far the most expensive option here. It needs a sandbox, a
  determinism story for fixture SHAs across Windows and Linux, a scoped git
  environment so the author's real global gitconfig cannot change a fixture's
  behaviour, and two `RepoQuery` implementations kept in agreement by a
  conformance suite. Phases 3 and 5 carry the project's widest error bars because
  of this decision, at 6 and 9 sessions.
- New risk introduced, and it is the one to watch: **assertions too loose to tell
  right from wrong.** A check that passes for both the correct solution and the
  naive one is worse than no check, because it reports green. Mitigated
  structurally — every scenario must ship naive counter-example command lists, and
  CI requires each to fail *exactly* the checks it declares in `expect_failures`,
  replayed through the real command policy.

## Alternatives considered

- **Expected-command matching**, possibly with regexes or a set of accepted
  variants. Rejected per the Context. The variant-set version is the tempting
  one: it looks like it fixes false negatives, but it still cannot distinguish
  "right tree, wrong method" from "right", which is the distinction the hard
  exercises are entirely about.
- **Compare the final tree hash to a golden repo.** Catches the false negatives
  cleanly, and fails the interesting half: `revert` and `reset --hard` can land on
  identical trees while differing completely in what they did to published
  history. A tree hash cannot see the reflog, the remote, or whether history was
  rewritten.
- **Multiple choice, or a free-text explanation graded by rubric.** Cheap to
  build, and back to grading recognition — plus rubric grading needs a model,
  which breaks the offline constraint.
- **Containers per attempt** to make the repo state easier to reason about.
  Orthogonal to *what* gets graded and much heavier; deferred to its own decision
  (ADR 0005, planned).

## Revisit if

Authoring a scenario routinely needs assertions the vocabulary cannot express. A
handful of additions is normal growth; needing an escape hatch that runs arbitrary
code to grade a scenario means the declarative model has failed and the decision
needs reopening.

## Validated before Phase 0 — 2026-09-30

Unusually for an ADR, this one was tested before the code existed. Two scenarios
were authored in full and run by hand against real git, specifically to find out
whether the assertion vocabulary could express them:
[`revert-a-pushed-commit`](../../content/git/revert-a-pushed-commit/) and
[`recover-a-lost-commit`](../../content/git/recover-a-lost-commit/). **It could,
with no additions** (PLAN.md §6.6).

The dry runs also surfaced four problems that were invisible on paper, including
the plan's own worked example missing a `fix-published` check — a solution that
reverted locally and never pushed would have passed every check while leaving the
build broken for the teammate the exercise is about. That is precisely the
"assertion too loose to tell right from wrong" failure listed above, found in the
plan's own example, which is the strongest available argument for the
counter-example requirement being mandatory rather than advisory.
