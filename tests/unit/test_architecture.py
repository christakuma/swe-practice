"""The boundary between layers, enforced rather than documented.

Dependencies point inward: `interface/ -> application/ -> domain/ <- adapters/`.
Nothing under `domain/` or `application/` may import from `adapters/` or
`interface/`, and nothing under `domain/` may import an I/O module at all.

The reason this is a test and not a paragraph in the README is the failure mode it
exists for: someone imports a concrete adapter into a use case because it is 3pm
and it works, nothing breaks, and the architecture claim quietly becomes false
while still being made. Rules without enforcement are suggestions (ADR 0002).

Two properties this file is careful about, because an architecture test that
cannot fail is worse than no architecture test:

* **The detector is itself tested.** The `test_the_detector_*` cases build module
  trees that violate each rule and assert the walk reports them. Without that, the
  suite passes just as happily when the detector is broken.
* **The walk is asserted to have found something.** A wrong root path, a renamed
  package, or a glob that matched no files would otherwise leave this green
  forever while checking nothing at all.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"
PACKAGE_ROOT = SOURCE_ROOT / "practice"

#: Layers that sit outside the core. Importing one from inside it inverts the
#: dependency arrow.
OUTER_LAYERS = ("practice.adapters", "practice.interface")

#: Modules that perform I/O or reach the outside world. `domain/` may not touch
#: any of them: the claim in PLAN.md §3 is that its tests run in milliseconds and
#: never touch a disk, and this is what makes that structural rather than lucky.
#:
#: `pathlib` is deliberately absent — `PurePosixPath` is pure, and a content
#: adapter handing the domain a parsed path is legitimate. `shlex` is likewise
#: pure string handling, which is why `CommandRun.command_line` may use it.
IO_MODULES = frozenset(
    {
        "http",
        "httpx",
        "io",
        "os",
        "requests",
        "shutil",
        "socket",
        "sqlite3",
        "ssl",
        "subprocess",
        "tempfile",
        "urllib",
        "webbrowser",
    }
)

INVERTED = "inward dependency inverted"
PERFORMS_IO = "performs I/O"


@dataclass(frozen=True, slots=True)
class Violation:
    module: str
    lineno: int
    imported: str
    reason: str

    def __str__(self) -> str:
        return f"{self.module}:{self.lineno} imports {self.imported} ({self.reason})"


@dataclass(frozen=True, slots=True)
class ScanResult:
    modules: tuple[str, ...]
    violations: tuple[Violation, ...]

    def reasons(self) -> list[str]:
        return [violation.reason for violation in self.violations]

    def describe(self) -> str:
        return "\n".join(f"  - {violation}" for violation in self.violations)


def module_name(path: Path, source_root: Path) -> str:
    """`src/practice/domain/ids.py` -> `practice.domain.ids`."""
    parts = list(path.relative_to(source_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def absolute_target(node: ast.ImportFrom, module: str, packages: Iterable[str]) -> str:
    """Resolve a relative import to the absolute module it names.

    Worth doing properly rather than prefix-matching the raw text: without it,
    `from ..adapters.git import GitRepoQuery` reads as a target of `adapters.git`
    and walks straight past the check — and a relative import is exactly the
    spelling someone reaching for a shortcut is most likely to write.

    A module resolves `.` against its containing package; a package resolves it
    against itself, which is why `packages` has to be passed in.
    """
    if not node.level:
        return node.module or ""
    parts = module.split(".")
    anchor = parts if module in packages else parts[:-1]
    base = anchor[: len(anchor) - (node.level - 1)]
    return ".".join([*base, node.module]) if node.module else ".".join(base)


def imported_modules(
    tree: ast.Module, module: str, packages: Iterable[str]
) -> Iterator[tuple[int, str]]:
    """Every module this file imports, one item per import target."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.lineno, absolute_target(node, module, packages)


def scan(root: Path, source_root: Path, *, forbid_io: bool) -> ScanResult:
    """Walk every module under `root` and report what it imports that it may not.

    The scanned module list comes back rather than being discarded, so a caller can
    assert the walk actually found the code it claims to police.
    """
    paths = sorted(root.rglob("*.py"))
    packages = frozenset(
        module_name(path, source_root) for path in paths if path.name == "__init__.py"
    )

    modules: list[str] = []
    violations: list[Violation] = []
    for path in paths:
        module = module_name(path, source_root)
        modules.append(module)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, target in imported_modules(tree, module, packages):
            if any(
                target == layer or target.startswith(f"{layer}.")
                for layer in OUTER_LAYERS
            ):
                violations.append(Violation(module, lineno, target, INVERTED))
            elif forbid_io and target.split(".", 1)[0] in IO_MODULES:
                violations.append(Violation(module, lineno, target, PERFORMS_IO))

    return ScanResult(tuple(modules), tuple(violations))


def scan_domain() -> ScanResult:
    return scan(PACKAGE_ROOT / "domain", SOURCE_ROOT, forbid_io=True)


# --- the boundary itself ---------------------------------------------------


def test_the_domain_does_not_import_an_adapter_or_the_interface() -> None:
    result = scan_domain()

    assert not [v for v in result.violations if v.reason == INVERTED], (
        f"the domain imports outward:\n{result.describe()}"
    )


def test_the_domain_performs_no_io() -> None:
    """PLAN.md §3 claims the domain has zero I/O. This is that claim, as a test."""
    result = scan_domain()

    assert not [v for v in result.violations if v.reason == PERFORMS_IO], (
        f"the domain performs I/O:\n{result.describe()}"
    )


def test_the_application_layer_does_not_import_an_adapter_or_the_interface() -> None:
    result = scan(PACKAGE_ROOT / "application", SOURCE_ROOT, forbid_io=True)

    assert not result.violations, (
        f"the application layer imports outward:\n{result.describe()}"
    )
    assert "practice.application" in result.modules


def test_the_walk_actually_found_the_domain() -> None:
    """A wrong root, a renamed package, or a glob that matched nothing would leave
    every assertion above vacuously true, and nothing else here would notice.
    """
    found = set(scan_domain().modules)

    assert {
        "practice.domain",
        "practice.domain.attempt",
        "practice.domain.checks",
        "practice.domain.checks.evaluation",
        "practice.domain.checks.refs",
        "practice.domain.checks.registry",
        "practice.domain.checks.trees",
        "practice.domain.commands",
        "practice.domain.errors",
        "practice.domain.exercise",
        "practice.domain.ids",
        "practice.domain.ports",
        "practice.domain.review",
        "practice.domain.verdict",
    } <= found


# --- the detector ----------------------------------------------------------


@pytest.fixture
def fake_tree(tmp_path: Path) -> Path:
    """A miniature `src/` for the detector to be pointed at.

    Nested a package deep — `domain/checks/` is where the real assertion functions
    live — so the relative-import cases resolve through more than one level.
    """
    checks = tmp_path / "practice" / "domain" / "checks"
    checks.mkdir(parents=True)
    for package in (tmp_path / "practice", checks.parent, checks):
        (package / "__init__.py").write_text("", encoding="utf-8")
    return tmp_path


def scan_fake(root: Path, body: str, *, forbid_io: bool = True) -> ScanResult:
    target = root / "practice" / "domain" / "checks" / "refs.py"
    target.write_text(body, encoding="utf-8")
    return scan(root / "practice" / "domain", root, forbid_io=forbid_io)


@pytest.mark.parametrize(
    "body",
    [
        "from practice.adapters.git import GitRepoQuery",
        "import practice.adapters.git",
        "from practice.interface.web.app import create_app",
        "from practice.adapters import content",
        "from ...adapters.git import GitRepoQuery",
        "from ...adapters import git",
        "from ...interface.cli.main import app",
    ],
)
def test_the_detector_catches_an_outward_import(fake_tree: Path, body: str) -> None:
    assert scan_fake(fake_tree, body).reasons() == [INVERTED]


@pytest.mark.parametrize(
    "body",
    [
        "import subprocess",
        "import sqlite3",
        "from subprocess import run",
        "import os.path",
        "from urllib.request import urlopen",
    ],
)
def test_the_detector_catches_an_io_import(fake_tree: Path, body: str) -> None:
    assert scan_fake(fake_tree, body).reasons() == [PERFORMS_IO]


@pytest.mark.parametrize(
    "body",
    [
        "from practice.domain.ids import Sha",
        "from pathlib import PurePosixPath",
        "import shlex",
        "from dataclasses import dataclass",
        "from . import registry",
        "from .. import errors",
        "from ..ids import Sha",
    ],
)
def test_the_detector_allows_what_the_domain_legitimately_needs(
    fake_tree: Path, body: str
) -> None:
    assert scan_fake(fake_tree, body).violations == ()


def test_the_detector_finds_a_violation_hidden_inside_a_function(
    fake_tree: Path,
) -> None:
    """A deferred import is the shortcut this is most likely to be smuggled in as,
    so the walk covers the whole tree rather than just module-level statements.
    """
    body = (
        "def build() -> object:\n"
        "    from practice.adapters.git import GitRepoQuery\n"
        "    return GitRepoQuery\n"
    )

    assert scan_fake(fake_tree, body).reasons() == [INVERTED]


def test_the_io_ban_is_only_applied_where_it_is_asked_for(fake_tree: Path) -> None:
    """Adapters exist to do I/O; the same walk must not condemn them for it."""
    assert scan_fake(fake_tree, "import subprocess", forbid_io=False).violations == ()


def test_a_violation_reads_as_a_usable_failure_message(fake_tree: Path) -> None:
    result = scan_fake(fake_tree, "from practice.adapters.git import GitRepoQuery")

    assert str(result.violations[0]) == (
        "practice.domain.checks.refs:1 imports practice.adapters.git "
        "(inward dependency inverted)"
    )


# --- where processes may be started ---------------------------------------


#: The only package allowed to start a process. Phase 3's trust split (PLAN.md
#: §8.1) rests on there being exactly one of these: fixtures get a shell, user
#: commands get an argv list, and both go through `adapters/sandbox/execution`.
#: A second `subprocess.run` anywhere would be a third path with neither
#: property, and the one most likely to be added in a hurry.
PROCESS_PACKAGE = "practice.adapters.sandbox"

#: Modules that start or signal a process.
PROCESS_MODULES = frozenset({"subprocess", "signal"})


def importers_of(targets: frozenset[str]) -> dict[str, list[str]]:
    """Every module under `src/practice` that imports one of `targets`."""
    paths = sorted(PACKAGE_ROOT.rglob("*.py"))
    packages = frozenset(
        module_name(path, SOURCE_ROOT) for path in paths if path.name == "__init__.py"
    )
    found: dict[str, list[str]] = {}
    for path in paths:
        module = module_name(path, SOURCE_ROOT)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for _, target in imported_modules(tree, module, packages):
            if target.split(".", 1)[0] in targets:
                found.setdefault(module, []).append(target)
    return found


def test_only_the_sandbox_starts_a_process() -> None:
    """One execution path, enforced.

    The trust split is only a split if there is a single place that starts
    processes. A `subprocess.run` added to, say, the kata runner or a CLI
    command would bypass the scoped environment, the output caps and the
    process-tree kill all at once — and would look perfectly reasonable in
    review.
    """
    offenders = {
        module: targets
        for module, targets in importers_of(PROCESS_MODULES).items()
        if not module.startswith(f"{PROCESS_PACKAGE}.") and module != PROCESS_PACKAGE
    }

    assert offenders == {}, (
        "processes must be started through adapters/sandbox/execution.py:\n"
        + "\n".join(
            f"  - {module} imports {targets}" for module, targets in offenders.items()
        )
    )


def test_the_sandbox_really_does_start_processes() -> None:
    """So the rule above cannot pass by there being no process code at all."""
    importers = importers_of(PROCESS_MODULES)

    assert f"{PROCESS_PACKAGE}.execution" in importers
