"""The assertion vocabulary: pure functions over `RepoQuery` and `Attempt`.

These live in the domain rather than under `adapters/` on purpose. They are pure
functions over a port — they never shell out — so putting them here makes
"testable without git installed" a structural fact rather than a happy accident,
and it puts the most correctness-critical code in the project inside the layer
the coverage gate and the architecture test actually police (PLAN.md §6.2, §9).

Phase 2 ships the `registry` — the set of names an `assert:` key may take — so
that a typo in `exercise.yaml` is a build failure rather than a silently skipped
assertion. The functions themselves arrive with the check engine in Phase 5.
"""
