"""The scoped environment, which is the whole reproducibility guarantee.

Unit tests rather than integration: building the mapping touches no filesystem
and starts no process, and every claim in PLAN.md §6.1 and §8.1 about what a
sandboxed process can and cannot see is a claim about this dictionary. Asserting
it here means the integration suite does not have to infer it from a commit
hash.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from practice.adapters.sandbox.env import (
    FIXTURE_EPOCH,
    FIXTURE_STEP,
    GitIdentity,
    SandboxPaths,
    sandbox_environment,
    system_path_entries,
    with_commit_date,
)

WORKSPACE = Path("/ws/ab12cd34") if os.name != "nt" else Path(r"C:\ws\ab12cd34")


def a_paths(root: Path = WORKSPACE) -> SandboxPaths:
    return SandboxPaths(
        home=root,
        repo=root / "repo",
        remotes=root / "remotes",
        tmp=root / "tmp",
        gitconfig=root / ".gitconfig",
        fixture_lib=root / "lib" / "fixture_lib.sh",
        aliases=root / "aliases",
        snapshot=root / "snapshot",
        clock=root / "clock",
    )


@pytest.fixture
def environment() -> dict[str, str]:
    return sandbox_environment(a_paths(), path_entries=("/usr/bin",))


# --- what cannot leak in ---------------------------------------------------


def test_the_real_home_cannot_be_reached(environment: dict[str, str]) -> None:
    """The single most important detail in PLAN.md §8.1.

    Both names, because Git for Windows falls back to `USERPROFILE` when `HOME`
    is unset — so setting only one of them leaves the developer's real git
    config reachable on exactly one of the two platforms in CI, which is the
    worst of the available outcomes.
    """
    assert environment["HOME"] == str(WORKSPACE)
    assert environment["USERPROFILE"] == str(WORKSPACE)


def test_git_config_is_scoped_to_the_workspace(environment: dict[str, str]) -> None:
    assert environment["GIT_CONFIG_GLOBAL"] == str(WORKSPACE / ".gitconfig")
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"


def test_nothing_ambient_is_inherited() -> None:
    """`os.environ` is never copied, and this is the test that keeps it true.

    A single `{**os.environ, ...}` would make every assertion in this file pass
    and still lose the guarantee, because the leaks that matter are variables
    nobody thought to override. So the assertion is about absence, using a
    variable that is certainly set in the parent and must not appear in the
    child.
    """
    marker = "PRACTICE_TEST_AMBIENT_MARKER"
    os.environ[marker] = "leaked"
    try:
        environment = sandbox_environment(a_paths(), path_entries=())
    finally:
        del os.environ[marker]

    assert marker not in environment


def test_inherited_git_variables_cannot_redirect_a_command() -> None:
    """`GIT_DIR` in the parent would point every command at another repository.

    The reason the environment is built rather than copied, in its most concrete
    form: a developer who has `GIT_DIR` exported — which `git` itself sets for
    hooks — would otherwise get fixtures built somewhere else entirely.
    """
    os.environ["GIT_DIR"] = "/somewhere/else/.git"
    try:
        environment = sandbox_environment(a_paths(), path_entries=())
    finally:
        del os.environ["GIT_DIR"]

    assert "GIT_DIR" not in environment
    assert "GIT_WORK_TREE" not in environment


def test_discovery_cannot_escape_the_workspace(environment: dict[str, str]) -> None:
    """A command run outside a repository should say so, not find one above."""
    assert environment["GIT_CEILING_DIRECTORIES"] == str(WORKSPACE)


# --- what cannot hang ------------------------------------------------------


def test_no_editor_can_be_launched(environment: dict[str, str]) -> None:
    """`git commit` with no `-m` has to fail, not stall.

    Without these it launches an editor, finds no terminal, and hangs until the
    command timeout expires — a ten second pause with no explanation, which
    PLAN.md §8.1 points out you would hit within five minutes of using the tool.
    """
    assert environment["GIT_EDITOR"] == "false"
    assert environment["GIT_SEQUENCE_EDITOR"] == "false"


def test_nothing_can_prompt_for_credentials(environment: dict[str, str]) -> None:
    """Every remote is a local bare repository, so a prompt is only ever a hang."""
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_messages_are_in_one_language(environment: dict[str, str]) -> None:
    """Reflog and porcelain parsing read these, and so does the solver."""
    assert environment["LC_ALL"] == "C"


# --- the fixture contract --------------------------------------------------


def test_the_fixture_contract_is_complete(environment: dict[str, str]) -> None:
    """Every variable `content/_lib/fixture_lib.sh` requires.

    The library refuses to run without them, by design — but it refuses with a
    bash parameter-expansion error, which is a worse way to find out than a
    failing test naming the variable.
    """
    for name in (
        "PRACTICE_FIXTURE_LIB",
        "PRACTICE_ALIASES",
        "PRACTICE_SNAPSHOT",
        "PRACTICE_REMOTES",
        "PRACTICE_CLOCK",
        "PRACTICE_EPOCH",
        "PRACTICE_STEP",
    ):
        assert environment[name], name


def test_fixture_paths_are_posix(environment: dict[str, str]) -> None:
    """The consumer is bash, including on Windows, where it is MSYS bash.

    A backslash in a path bash is about to `source` is an escape character, so
    `C:\\ws\\lib\\fixture_lib.sh` would be read as `C:wslibfixture_lib.sh`.
    """
    assert "\\" not in environment["PRACTICE_FIXTURE_LIB"]
    assert environment["PRACTICE_FIXTURE_LIB"].endswith("lib/fixture_lib.sh")


def test_the_clock_constants_are_passed_in_rather_than_duplicated(
    environment: dict[str, str],
) -> None:
    """One definition of the epoch and the step, in Python.

    The bash library used to hold its own copies. Two copies would drift, and
    the symptom would be every hash in `content/fixtures.lock` changing with no
    visible cause.
    """
    assert environment["PRACTICE_EPOCH"] == str(FIXTURE_EPOCH)
    assert environment["PRACTICE_STEP"] == str(FIXTURE_STEP)


# --- identity and dates ----------------------------------------------------


def test_the_identity_is_pinned_on_both_sides(environment: dict[str, str]) -> None:
    """Author and committer are both inputs to a commit hash (PLAN.md §6.1)."""
    assert environment["GIT_AUTHOR_NAME"] == environment["GIT_COMMITTER_NAME"]
    assert environment["GIT_AUTHOR_EMAIL"] == environment["GIT_COMMITTER_EMAIL"]
    assert environment["GIT_AUTHOR_EMAIL"].endswith(".invalid")


def test_a_custom_identity_is_used_for_both() -> None:
    environment = sandbox_environment(
        a_paths(),
        path_entries=(),
        identity=GitIdentity(name="Someone", email="someone@example.invalid"),
    )

    assert environment["GIT_COMMITTER_NAME"] == "Someone"


def test_dates_are_absent_until_a_commit_time_is_chosen(
    environment: dict[str, str],
) -> None:
    """The base environment carries no dates.

    Deliberate: the dates are the one part that changes per command, and a base
    mapping that carried a stale pair would silently date a commit to whenever
    the workspace was provisioned if a caller forgot `with_commit_date`.
    """
    assert "GIT_AUTHOR_DATE" not in environment


def test_a_commit_date_is_set_on_both_sides(environment: dict[str, str]) -> None:
    dated = with_commit_date(environment, 1709542800)

    assert dated["GIT_AUTHOR_DATE"] == "@1709542800 +0000"
    assert dated["GIT_COMMITTER_DATE"] == "@1709542800 +0000"


def test_setting_a_date_does_not_mutate_the_original(
    environment: dict[str, str],
) -> None:
    """The base environment is built once per workspace and dated per command."""
    with_commit_date(environment, 1709542800)

    assert "GIT_AUTHOR_DATE" not in environment


# --- PATH ------------------------------------------------------------------


def test_path_is_assembled_from_what_it_is_given(environment: dict[str, str]) -> None:
    assert environment["PATH"] == "/usr/bin"


def test_path_entries_are_joined_the_way_the_platform_expects() -> None:
    environment = sandbox_environment(a_paths(), path_entries=("one", "two"))

    assert environment["PATH"] == f"one{os.pathsep}two"


def test_the_system_path_is_platform_appropriate() -> None:
    """Needed on Windows because Git for Windows shells out to `cmd`, and on
    POSIX because fixtures call coreutils.
    """
    entries = system_path_entries()

    assert entries
    if os.name == "nt":
        assert any("System32" in entry for entry in entries)
    else:
        assert "/usr/bin" in entries
