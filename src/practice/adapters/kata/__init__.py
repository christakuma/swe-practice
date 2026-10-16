"""The kata engine: run a hidden test suite, turn the results into a verdict.

Three modules, split by what each one knows about:

* `report_plugin` — a pytest plugin that writes one JSON record per test. Knows
  about pytest's hooks, and **nothing about this project**: it is copied into
  the workspace and imported by a different interpreter invocation.
* `pytest_runner` — the pinned invocation, the files it installs, and the
  parsing of what comes back. Knows about subprocess arguments and encodings.
* `grader` — records become `CheckReport`s become a `Verdict`. Knows about the
  domain.

And a pair beside them since ADR 0029, for the "Run" button: `examples_harness`
is copied in and run like the plugin, and `examples` is its runner, holding the
same lock as `pytest_runner` because both write `solution.py`.

The oracle here is obvious in a way the git engine's is not — run the tests —
so the interesting content is not the grading logic but the pinning. Every
argument in `pytest_runner._ARGV` is there because a default lets something
outside the workspace change a verdict, and three of them were added only
after running the thing (PLAN.md §7, §16).
"""

from practice.adapters.kata.examples import KataExampleRunner, parse_trial
from practice.adapters.kata.grader import KataGrader, KataRunner, KataRunnerError
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
    "KataExampleRunner",
    "KataGrader",
    "KataRun",
    "KataRunner",
    "KataRunnerError",
    "PytestKataRunner",
    "TestOutcome",
    "TestRecord",
    "mechanism_files",
    "parse_records",
    "parse_trial",
    "plugin_source",
]
