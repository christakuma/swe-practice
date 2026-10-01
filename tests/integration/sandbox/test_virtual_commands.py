"""The file commands that exist because there is no shell.

Integration tests, because every one of these is about what ends up on disk —
`write` producing LF on Windows, `rm` refusing a directory, `ls` hiding `.git`.
A fake filesystem would let the interesting half of them pass while being wrong.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.sandbox.execution import TRUNCATION_MARKER
from practice.adapters.sandbox.virtual_commands import (
    VIRTUAL_COMMANDS,
    is_virtual,
    run_virtual,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository directory with one file and a `.git` to not list."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    (root / ".git").mkdir()
    return root


# --- the set itself --------------------------------------------------------


def test_every_virtual_command_has_an_implementation(repo: Path) -> None:
    """A name in one place and not the other is either unreachable code or a
    `command not found` on something the policy already permitted — and the
    second one would only be found by a solver, mid-exercise.

    Each one is dispatched rather than merely looked up, because the dispatch
    table is the thing that can disagree with the set.
    """
    for name in sorted(VIRTUAL_COMMANDS):
        assert is_virtual(name)
        result = run_virtual([name, "--nonsense-argument"], root=repo)

        assert "not a virtual command" not in result.stderr, name


def test_pwd_is_virtual() -> None:
    """Found by building rather than by designing.

    PLAN.md §8.1 lists six commands and `pwd` is not among them, but
    `content/git/revert-a-pushed-commit` had already shipped `pwd` in its
    allowlist — and `pwd` is a shell builtin with no executable behind it on
    Windows. Without it here, a solver typing a command the exercise explicitly
    permits would get `command not found`.
    """
    assert is_virtual("pwd")


def test_git_is_not_virtual() -> None:
    assert not is_virtual("git")


# --- write and append ------------------------------------------------------


def test_write_replaces_a_file(repo: Path) -> None:
    result = run_virtual(["write", "README.md", "replaced"], root=repo)

    assert result.succeeded
    assert (repo / "README.md").read_text(encoding="utf-8") == "replaced\n"


def test_write_takes_one_line_per_argument(repo: Path) -> None:
    run_virtual(["write", "notes.md", "first", "second"], root=repo)

    assert (repo / "notes.md").read_text(encoding="utf-8") == "first\nsecond\n"


def test_write_with_no_lines_truncates(repo: Path) -> None:
    """What `> file` does, and the reason anyone reaches for redirection."""
    run_virtual(["write", "README.md"], root=repo)

    assert (repo / "README.md").read_text(encoding="utf-8") == ""


def test_write_always_produces_lf(repo: Path) -> None:
    """The `core.autocrlf` problem from the other side (PLAN.md §6.1).

    Python would write CRLF on Windows by default. That changes the blob, so the
    tree, so every commit hash after it — which is exactly what the pinned git
    config and `.gitattributes` exist to prevent, reintroduced by our own tool.
    """
    run_virtual(["write", "notes.md", "one", "two"], root=repo)

    assert b"\r" not in (repo / "notes.md").read_bytes()


def test_append_adds_to_the_end(repo: Path) -> None:
    result = run_virtual(["append", "README.md", "more"], root=repo)

    assert result.succeeded
    assert (repo / "README.md").read_text(encoding="utf-8") == "hello\nmore\n"


def test_append_creates_a_missing_file(repo: Path) -> None:
    run_virtual(["append", "new.md", "line"], root=repo)

    assert (repo / "new.md").read_text(encoding="utf-8") == "line\n"


def test_write_without_a_path_is_a_usage_error(repo: Path) -> None:
    result = run_virtual(["write"], root=repo)

    assert result.exit_code == 2
    assert "usage" in result.stderr


# --- cat -------------------------------------------------------------------


def test_cat_prints_a_file(repo: Path) -> None:
    result = run_virtual(["cat", "README.md"], root=repo)

    assert result.stdout == "hello\n"


def test_cat_concatenates_in_order(repo: Path) -> None:
    (repo / "b.txt").write_text("b\n", encoding="utf-8")

    result = run_virtual(["cat", "b.txt", "README.md"], root=repo)

    assert result.stdout == "b\nhello\n"


def test_cat_on_a_missing_file_fails_like_the_real_one(repo: Path) -> None:
    result = run_virtual(["cat", "absent.md"], root=repo)

    assert result.exit_code == 1
    assert "No such file or directory" in result.stderr


def test_cat_on_a_directory_fails(repo: Path) -> None:
    result = run_virtual(["cat", "."], root=repo)

    assert "Is a directory" in result.stderr


def test_cat_survives_a_file_that_is_not_text(repo: Path) -> None:
    """A solver can commit any bytes they like, and `cat` should print mojibake
    like the real one rather than raise.
    """
    (repo / "blob.bin").write_bytes(b"\xff\xfe\x00binary")

    result = run_virtual(["cat", "blob.bin"], root=repo)

    assert result.succeeded


def test_cat_output_is_capped(repo: Path) -> None:
    (repo / "big.txt").write_text("x" * 5000, encoding="utf-8")

    result = run_virtual(["cat", "big.txt"], root=repo, output_limit=1000)

    assert result.truncated
    assert result.stdout.endswith(TRUNCATION_MARKER)


# --- ls --------------------------------------------------------------------


def test_ls_lists_the_repository(repo: Path) -> None:
    result = run_virtual(["ls"], root=repo)

    assert result.stdout == "README.md\n"


def test_ls_hides_dotfiles_so_git_does_not_dominate(repo: Path) -> None:
    """`.git` is a dotfile, so the real `ls` hides it too.

    Worth a test rather than left to chance: a bare `ls` that listed `.git`
    would make every listing in every exercise about plumbing instead of about
    the solver's files.
    """
    assert ".git" not in run_virtual(["ls"], root=repo).stdout


def test_ls_minus_a_shows_them(repo: Path) -> None:
    result = run_virtual(["ls", "-a"], root=repo)

    assert ".git/" in result.stdout


def test_ls_marks_directories(repo: Path) -> None:
    (repo / "src").mkdir()

    assert "src/" in run_virtual(["ls"], root=repo).stdout


def test_ls_of_a_missing_path_fails(repo: Path) -> None:
    result = run_virtual(["ls", "absent"], root=repo)

    assert result.exit_code == 1
    assert "cannot access" in result.stderr


def test_ls_of_several_paths_labels_them(repo: Path) -> None:
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("", encoding="utf-8")

    result = run_virtual(["ls", ".", "src"], root=repo)

    assert "src:" in result.stdout
    assert "app.py" in result.stdout


# --- mkdir -----------------------------------------------------------------


def test_mkdir_creates_a_directory(repo: Path) -> None:
    result = run_virtual(["mkdir", "src"], root=repo)

    assert result.succeeded
    assert (repo / "src").is_dir()


def test_mkdir_without_p_refuses_a_missing_parent(repo: Path) -> None:
    """Keeping the real behaviour, so `-p` is not learned as decoration."""
    result = run_virtual(["mkdir", "a/b"], root=repo)

    assert result.exit_code == 1
    assert not (repo / "a").exists()


def test_mkdir_p_creates_parents(repo: Path) -> None:
    result = run_virtual(["mkdir", "-p", "a/b/c"], root=repo)

    assert result.succeeded
    assert (repo / "a" / "b" / "c").is_dir()


def test_mkdir_without_p_refuses_an_existing_directory(repo: Path) -> None:
    (repo / "src").mkdir()

    result = run_virtual(["mkdir", "src"], root=repo)

    assert "File exists" in result.stderr


def test_mkdir_p_is_idempotent(repo: Path) -> None:
    (repo / "src").mkdir()

    assert run_virtual(["mkdir", "-p", "src"], root=repo).succeeded


# --- rm --------------------------------------------------------------------


def test_rm_removes_a_file(repo: Path) -> None:
    result = run_virtual(["rm", "README.md"], root=repo)

    assert result.succeeded
    assert not (repo / "README.md").exists()


def test_rm_refuses_a_directory_without_r(repo: Path) -> None:
    """An exercise about recovering from a destructive command should not ship
    an `rm` that is quieter than the real one.
    """
    (repo / "src").mkdir()

    result = run_virtual(["rm", "src"], root=repo)

    assert "Is a directory" in result.stderr
    assert (repo / "src").is_dir()


def test_rm_r_removes_a_tree(repo: Path) -> None:
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("", encoding="utf-8")

    assert run_virtual(["rm", "-r", "src"], root=repo).succeeded
    assert not (repo / "src").exists()


def test_rm_rf_is_accepted_as_one_flag(repo: Path) -> None:
    """Because that is how everyone types it."""
    (repo / "src").mkdir()

    assert run_virtual(["rm", "-rf", "src"], root=repo).succeeded


def test_rm_on_a_missing_file_fails(repo: Path) -> None:
    result = run_virtual(["rm", "absent"], root=repo)

    assert result.exit_code == 1
    assert "cannot remove" in result.stderr


def test_rm_f_on_a_missing_file_succeeds(repo: Path) -> None:
    assert run_virtual(["rm", "-f", "absent"], root=repo).succeeded


# --- pwd -------------------------------------------------------------------


def test_pwd_prints_the_repository(repo: Path) -> None:
    result = run_virtual(["pwd"], root=repo)

    assert result.stdout.strip() == repo.resolve().as_posix()


def test_pwd_takes_no_arguments(repo: Path) -> None:
    assert run_virtual(["pwd", "somewhere"], root=repo).exit_code == 2


# --- the boundary ----------------------------------------------------------


def test_a_path_outside_the_repository_is_refused(repo: Path) -> None:
    """Not a security boundary — the solver owns the machine (PLAN.md §8.1).

    It is a blast-radius boundary: `write ../../.bashrc` is almost certainly a
    typo, and the useful answer to a typo is a refusal that says where the edge
    is.
    """
    result = run_virtual(["write", "../escaped.txt", "x"], root=repo)

    assert result.exit_code == 1
    assert "outside the repository" in result.stderr
    assert not (repo.parent / "escaped.txt").exists()


def test_an_absolute_path_is_refused(repo: Path) -> None:
    target = repo.parent / "absolute.txt"

    result = run_virtual(["write", str(target), "x"], root=repo)

    assert "absolute paths" in result.stderr
    assert not target.exists()


def test_a_path_that_escapes_and_returns_is_allowed(repo: Path) -> None:
    """`src/../README.md` resolves back inside, so refusing it would be wrong.

    Resolution before the check rather than a textual scan for `..`, which is
    the implementation that would get this backwards.
    """
    result = run_virtual(["cat", "./README.md"], root=repo)

    assert result.succeeded


def test_rm_cannot_delete_the_repository_itself(repo: Path) -> None:
    """`rm -rf .` would take the `.git` directory with it and leave an attempt
    that cannot be graded, in a way that looks like a tool bug rather than
    something the solver did.
    """
    result = run_virtual(["rm", "-rf", "."], root=repo)

    assert not result.succeeded
    assert repo.is_dir()
