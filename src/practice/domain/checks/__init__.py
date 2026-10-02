"""The assertion vocabulary: pure functions over `RepoQuery` and `Attempt`.

These live in the domain rather than under `adapters/` on purpose. They are pure
functions over a port — they never shell out — so putting them here makes
"testable without git installed" a structural fact rather than a happy accident,
and it puts the most correctness-critical code in the project inside the layer
the coverage gate and the architecture test actually police (PLAN.md §6.2, §9).

Six modules, split by what each family reads:

* `evaluation` — what an assertion is handed and what it hands back.
  `CheckContext`, `CheckResult`, `Params`, and the alias resolution every
  revision goes through before git sees it.
* `refs` — refs, ancestry, and the shape of history. The family that does the
  actual discriminating, because content alone cannot tell a revert from a reset.
* `trees` — file content, committed and in the working tree.
* `worktree` — the working tree and the index.
* `recovery` — where git keeps the things you thought you had destroyed.
* `process` — the `Attempt` command log rather than the repository. Advisory by
  convention: these grade craft, not correctness.

`registry` is the dispatch table over all of them, and the one place `not:` is
applied.
"""
