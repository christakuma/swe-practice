"""The kata engine: run a hidden test suite, turn the results into a verdict.

Two modules so far, split by what each one knows about:

* `report_plugin` — a pytest plugin that writes one JSON record per test. Knows
  about pytest's hooks, and **nothing about this project**: it is copied into
  the workspace and imported by a different interpreter invocation.
* `pytest_runner` — the pinned invocation, the files it installs, and the
  parsing of what comes back. Knows about subprocess arguments and encodings.

`grader`, which turns those records into a `Verdict`, follows in the next
commit.

The oracle here is obvious in a way the git engine's is not — run the tests —
so the interesting content is not the grading logic but the pinning. Every
argument in `pytest_runner._ARGV` is there because a default lets something
outside the workspace change a verdict, and three of them were added only after
running the thing (PLAN.md §7, §16).
"""

from practice.adapters.kata.pytest_runner import (
    CONFTEST,
    PLUGIN_MODULE,
    KataRun,
    PytestKataRunner,
    TestOutcome,
    TestRecord,
    mechanism_files,
    parse_records,
    plugin_source,
)

__all__ = [
    "CONFTEST",
    "PLUGIN_MODULE",
    "KataRun",
    "PytestKataRunner",
    "TestOutcome",
    "TestRecord",
    "mechanism_files",
    "parse_records",
    "plugin_source",
]
