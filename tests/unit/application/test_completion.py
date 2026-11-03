"""`complete`: which word is being completed, and with what.

Pure, so every rule is one line of input against one vocabulary. The cases
are grouped by the question the function answers first: which position is
the cursor in, and therefore which list does the word come from.
"""

from __future__ import annotations

import pytest

from practice.application.completion import Completion, Vocabulary, complete

WORDS = Vocabulary(
    programs=frozenset({"git", "ls", "cat", "write"}),
    revisions=frozenset(
        {"HEAD", "main", "feature/webhooks", "feature/cache", "origin/main"}
    ),
    paths=frozenset(
        {"README.md", "retry.py", "tools/healthcheck.sh", "tools/deploy.sh", ".env"}
    ),
)


def line_after(line: str) -> str:
    return complete(line, WORDS).line


# --- the first word, and git's second ----------------------------------------


def test_the_first_word_completes_to_an_allowed_program() -> None:
    assert line_after("gi") == "git "


def test_a_program_the_exercise_does_not_allow_is_not_offered() -> None:
    assert complete("pyt", WORDS) == Completion(line="pyt", matches=())


def test_the_word_after_git_completes_to_a_subcommand() -> None:
    assert line_after("git stas") == "git stash "
    assert complete("git sta", WORDS).matches == ("stash", "status")


def test_a_unique_subcommand_is_finished_with_a_space() -> None:
    assert line_after("git cherr") == "git cherry-pick "


def test_an_empty_word_after_git_lists_every_subcommand() -> None:
    done = complete("git ", WORDS)

    assert done.line == "git "
    assert "rebase" in done.matches
    assert "rev-parse" not in done.matches


def test_stash_and_bisect_take_an_operation_next() -> None:
    assert line_after("git stash po") == "git stash pop "
    assert line_after("git bisect go") == "git bisect good "


# --- revisions and paths --------------------------------------------------------


def test_a_revision_argument_completes_to_a_branch() -> None:
    assert line_after("git checkout feature/w") == "git checkout feature/webhooks "


def test_shared_prefixes_extend_as_far_as_every_match_agrees() -> None:
    done = complete("git rebase fe", WORDS)

    assert done.line == "git rebase feature/"
    assert done.matches == ("feature/cache", "feature/webhooks")


def test_a_second_word_after_an_operation_is_a_revision() -> None:
    assert line_after("git stash show ma") == "git stash show main "


def test_a_program_other_than_git_takes_paths() -> None:
    assert line_after("cat re") == "cat retry.py "


def test_a_directory_completes_one_level_with_no_space() -> None:
    assert line_after("cat to") == "cat tools/"


def test_inside_a_directory_the_files_are_offered_whole() -> None:
    assert line_after("cat tools/h") == "cat tools/healthcheck.sh "


def test_ignored_files_are_offered_like_any_other() -> None:
    """A shell completes `.env`; it is on disk, and `cat` is how you check it."""
    assert line_after("cat .e") == "cat .env "


def test_subcommands_that_take_files_complete_paths() -> None:
    assert line_after("git add RE") == "git add README.md "


def test_after_a_double_dash_everything_is_a_path() -> None:
    assert line_after("git checkout main~3 -- tools/d") == (
        "git checkout main~3 -- tools/deploy.sh "
    )


def test_a_revision_and_colon_completes_the_path_after_it() -> None:
    assert line_after("git show main~3:tools/he") == (
        "git show main~3:tools/healthcheck.sh "
    )


# --- what it declines -----------------------------------------------------------


def test_flags_are_never_completed() -> None:
    """A Tab key teaches what it offers; see the module docstring."""
    assert complete("git log --one", WORDS) == Completion(
        line="git log --one", matches=()
    )


def test_inside_an_open_quote_nothing_is_completed() -> None:
    assert complete("write notes.md 'some re", WORDS).matches == ()


@pytest.mark.parametrize("line", ["", "   "])
def test_an_empty_line_offers_every_program(line: str) -> None:
    done = complete(line, WORDS)

    assert done.line == line
    assert done.matches == ("cat", "git", "ls", "write")


def test_a_word_that_matches_nothing_leaves_the_line_alone() -> None:
    assert complete("git checkout nope", WORDS) == Completion(
        line="git checkout nope", matches=()
    )


def test_completion_only_touches_the_last_word() -> None:
    assert line_after("git   checkout  ma") == "git   checkout  main "


def test_the_first_argument_of_push_is_a_remote() -> None:
    words = Vocabulary(
        programs=WORDS.programs,
        revisions=WORDS.revisions,
        paths=WORDS.paths,
        remotes=frozenset({"origin", "upstream"}),
    )

    assert complete("git push or", words).line == "git push origin "
    assert complete("git push origin ma", words).line == "git push origin main "
