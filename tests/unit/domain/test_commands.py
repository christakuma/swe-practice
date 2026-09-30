"""Parsing a typed line into an argv, and a `.cmds` file into a list of them."""

from __future__ import annotations

import pytest

from practice.domain.commands import (
    CommandLine,
    parse_command_line,
    parse_command_list,
)
from practice.domain.errors import InvalidValueError


class TestParseCommandLine:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("git status", ("git", "status")),
            ("  git   status  ", ("git", "status")),
            ("git revert --no-edit HEAD", ("git", "revert", "--no-edit", "HEAD")),
            # Quoting survives, because a commit message is one argument.
            ('git commit -m "fix it"', ("git", "commit", "-m", "fix it")),
            ("git commit -m 'fix it'", ("git", "commit", "-m", "fix it")),
            # A bare `$` is not command substitution and not a shell character.
            ("cat cost$.txt", ("cat", "cost$.txt")),
            ("write src/parser.py hello", ("write", "src/parser.py", "hello")),
        ],
    )
    def test_a_legal_line_becomes_an_argv(
        self, line: str, expected: tuple[str, ...]
    ) -> None:
        assert parse_command_line(line) == expected

    @pytest.mark.parametrize(
        "line",
        [
            "echo hi > out.txt",
            "cat out.txt | grep x",
            "git log < input",
            "git status & git log",
            "git status; git log",
            "git show `git rev-parse HEAD`",
        ],
    )
    def test_a_shell_character_is_rejected(self, line: str) -> None:
        with pytest.raises(InvalidValueError, match="no shell here"):
            parse_command_line(line)

    def test_a_backslash_is_an_escape_not_a_path_separator(self) -> None:
        """A sharp edge, documented rather than papered over. `shlex` in POSIX
        mode eats backslashes, so `src\file.txt` arrives as `srcfile.txt`.

        That is the right behaviour to keep: repository paths are forward-slashed
        everywhere in this project — `WorktreeStatus` promises it — so a content
        author reaching for a backslash has a bug regardless. Turning POSIX mode
        off to accommodate it would break quoting, which every commit message
        needs.
        """
        assert parse_command_line(r"cat src\parser.py") == ("cat", "srcparser.py")

    def test_the_rejection_names_the_alternative(self) -> None:
        """The point of refusing `>` is to teach `write`, not to say no."""
        with pytest.raises(InvalidValueError, match="write, append, rm, mkdir"):
            parse_command_line("echo hi > out.txt")

    def test_command_substitution_is_rejected(self) -> None:
        with pytest.raises(InvalidValueError, match="command substitution"):
            parse_command_line("git show $(git rev-parse HEAD)")

    def test_an_unbalanced_quote_is_a_clean_error_not_a_traceback(self) -> None:
        with pytest.raises(InvalidValueError, match="cannot be split"):
            parse_command_line('git commit -m "unfinished')

    @pytest.mark.parametrize("line", ["", "   ", "\t"])
    def test_an_empty_line_is_not_a_command(self, line: str) -> None:
        with pytest.raises(InvalidValueError, match="is not a command"):
            parse_command_line(line)

    def test_the_error_is_also_a_value_error(self) -> None:
        """Load-bearing: the content schema calls this inside a Pydantic field
        validator, and Pydantic only attaches a field path to a `ValueError`.
        """
        with pytest.raises(ValueError, match="no shell here"):
            parse_command_line("a | b")


class TestParseCommandList:
    def test_blank_lines_and_comments_are_ignored(self) -> None:
        text = (
            "# Reference solution.\n"
            "\n"
            "git log --oneline\n"
            "   \n"
            "  # indented comment\n"
            "git revert --no-edit HEAD\n"
        )

        assert [command.argv for command in parse_command_list(text)] == [
            ("git", "log", "--oneline"),
            ("git", "revert", "--no-edit", "HEAD"),
        ]

    def test_line_numbers_count_the_source_file_not_the_commands(self) -> None:
        """They end up in a validation message, so they have to match what the
        author's editor shows, not an index into the lines that survived.
        """
        text = "# header\n\ngit status\n\ngit log\n"

        assert [command.lineno for command in parse_command_list(text)] == [3, 5]

    def test_a_hash_inside_a_command_is_an_argument_not_a_comment(self) -> None:
        """Whole-line comments only: `--format=%h#%s` must survive intact."""
        (command,) = parse_command_list("git log --format=%h#%s\n")

        assert command.argv == ("git", "log", "--format=%h#%s")

    def test_a_bad_line_is_reported_with_its_number_and_its_text(self) -> None:
        text = "git status\necho hi > out.txt\n"

        with pytest.raises(InvalidValueError, match=r"line 2: 'echo hi > out\.txt'"):
            parse_command_list(text)

    def test_an_empty_file_parses_to_nothing(self) -> None:
        """Whether an empty solution is legal is the content suite's call, not
        the parser's — it reports what is there.
        """
        assert parse_command_list("# nothing but a comment\n") == ()

    def test_a_file_with_crlf_endings_parses(self) -> None:
        """`.gitattributes` pins `*.cmds` to LF, but a file that reaches the
        parser some other way should not fail on a stray `\r`.
        """
        (command,) = parse_command_list("git status\r\n")

        assert command.argv == ("git", "status")


class TestCommandLine:
    def test_program_is_the_first_argument(self) -> None:
        assert CommandLine(lineno=1, argv=("git", "status")).program == "git"

    def test_text_normalises_spacing_the_way_the_attempt_log_does(self) -> None:
        """Process assertions match patterns against this rendering, so a line
        read from a `.cmds` file and the same line typed by a solver have to
        produce the same string.
        """
        command = CommandLine(lineno=1, argv=("git", "commit", "-m", "fix it"))

        assert command.text == "git commit -m 'fix it'"

    def test_an_empty_argv_is_refused(self) -> None:
        with pytest.raises(InvalidValueError, match="needs an argv"):
            CommandLine(lineno=1, argv=())
