"""A pytest plugin that writes one JSON record per test.

**This file is copied into the workspace and imported by a different
interpreter invocation**, which is the only unusual thing about it and the
reason for every constraint below:

* **It imports nothing from `practice`.** The subprocess runs in isolated mode
  with the workspace as its only added `sys.path` entry, so an import of the
  application package would fail — and if it succeeded it would mean the graded
  process could see the grader, which is the isolation this phase exists to
  keep.
* **It is written by hand rather than pulled from `pytest-json-report`.** Forty
  lines, one less dependency, and it produces exactly the shape
  `pytest_runner` wants instead of a general one it would have to translate
  (PLAN.md §7).
* **It cannot be loaded with `-p`.** `-p` takes a module name, and `python -I`
  implies `-P`, so the workspace is not on `sys.path` when pytest resolves the
  argument — proven by running it, which fails with `No module named
  'practice_report'` before collection starts. The copied-in `conftest.py`
  registers it through `pytest_plugins` instead, by which point pytest has
  imported the conftest by path and the workspace is importable. See
  `pytest_runner.CONFTEST`.

The docstring harvest is the one thing here that is not bookkeeping. §7 uses a
test's docstring as the human-readable `label` on its `CheckReport`, so the
content author's sentence about what the solution must do is what a solver
reads — not `test_does_not_pair_an_element_with_itself`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

__all__ = ["REPORT_OPTION", "SCHEMA_VERSION"]

#: Bumped if the record shape changes. `pytest_runner` refuses a document it
#: does not recognise rather than reading fields that may have moved — the
#: plugin in a workspace is a *copy*, and a resumed attempt can be holding one
#: written by an older version of this file.
SCHEMA_VERSION = 1

#: Where to write. An option rather than a fixed filename so the runner names
#: the file, and an option rather than an environment variable because `-I`
#: implies `-E` and would drop a `PYTHON`-prefixed one.
REPORT_OPTION = "--report-out"

#: Per-test message cap. Generous for an assertion diff on a single function,
#: and small enough that a test asserting on a 20,000-element list cannot put a
#: megabyte of repr into the verdict panel.
_MESSAGE_LIMIT = 1200

_DOCSTRINGS: dict[str, str] = {}
_RECORDS: dict[str, dict[str, Any]] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(REPORT_OPTION, action="store", default="report.json")


def pytest_collection_modifyitems(items: Sequence[pytest.Item]) -> None:
    """Harvest docstrings at collection, where the test function is reachable.

    A report object knows a nodeid and an outcome but not the function it came
    from, so the label has to be collected here and joined on afterwards.
    """
    for item in items:
        doc = getattr(getattr(item, "obj", None), "__doc__", None)
        if doc:
            _DOCSTRINGS[item.nodeid] = doc


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Fold a test's three phases into one record.

    pytest reports setup, call and teardown separately; a `CheckReport` is one
    per test. The phase is kept in the outcome rather than discarded, because a
    failure in setup is a broken test suite and a failure in the call is a
    wrong solution — and telling a solver the second when it was the first
    sends them looking in the wrong file.
    """
    record = _RECORDS.setdefault(
        report.nodeid,
        {
            "nodeid": report.nodeid,
            "outcome": "passed",
            "message": None,
            "location": None,
            "duration_ms": 0,
        },
    )
    record["duration_ms"] += round(report.duration * 1000)

    if report.failed:
        crash = getattr(report.longrepr, "reprcrash", None)
        record["outcome"] = "failed" if report.when == "call" else "error"
        message = crash.message if crash is not None else str(report.longrepr)
        record["message"] = message[:_MESSAGE_LIMIT]
        if crash is not None:
            # The basename, never the path: the workspace path is a temp
            # directory whose name changes every run, and a verdict that
            # differs between two identical attempts is not a verdict.
            record["location"] = f"{Path(crash.path).name}:{crash.lineno}"
    elif report.skipped and record["outcome"] == "passed":
        record["outcome"] = "skipped"


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write the report, whatever happened.

    `sessionfinish` runs even when collection failed and no test executed,
    which is the case that matters: a report holding zero tests and a non-zero
    exit status is how the runner learns the difference between "the solution
    is wrong" and "the suite never ran".
    """
    for nodeid, record in _RECORDS.items():
        record["doc"] = _DOCSTRINGS.get(nodeid)

    document = {
        "version": SCHEMA_VERSION,
        "exit_status": int(exitstatus),
        "tests": list(_RECORDS.values()),
    }
    destination = Path(str(session.config.getoption(REPORT_OPTION)))
    destination.write_text(
        json.dumps(document, indent=1) + "\n", encoding="utf-8", newline=""
    )
