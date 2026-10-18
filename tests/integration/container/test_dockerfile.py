"""The Dockerfile parser and process composition, on inputs chosen to be awkward.

Every PID 1 expectation in `TestWhatPid1Becomes` was **measured** against
`python:3.12-slim` before it was written here (ADR 0030): dash does not exec a
lone `sh -c` command, the shell's own `exec` does, and bash execs the last
command of an `&&` list. A case that encoded the folklore instead would have
been the kind of claim ADR 0022 says is a guess.
"""

from __future__ import annotations

import pytest

from practice.adapters.container.dockerfile import (
    DockerfileError,
    compose_process,
    lineage,
    parse,
)


def process(text: str) -> tuple[str, ...]:
    return compose_process(parse(text))


class TestReadingInstructions:
    def test_a_comment_inside_a_continuation_does_not_end_it(self) -> None:
        [stage] = parse(
            "FROM python:3.12-slim\n"
            "RUN apt-get update \\\n"
            "    # pinned for reproducibility\n"
            "    && apt-get install -y curl\n"
        )
        [run] = stage.instructions
        assert run.args == ("apt-get update && apt-get install -y curl",)
        assert run.line == 2

    def test_a_blank_line_inside_a_continuation_does_not_end_it(self) -> None:
        """Docker warns and keeps joining; ending the RUN made `&&` a keyword."""
        [stage] = parse(
            "FROM python:3.12-slim\n"
            "RUN apt-get update \\\n"
            "\n"
            "    && apt-get install -y curl\n"
        )
        [run] = stage.instructions
        assert run.args == ("apt-get update && apt-get install -y curl",)

    def test_a_tab_separates_the_keyword(self) -> None:
        [stage] = parse("FROM python:3.12-slim\nRUN\tpip install x\n")
        [run] = stage.instructions
        assert (run.keyword, run.args) == ("RUN", ("pip install x",))

    def test_the_escape_directive_is_honoured(self) -> None:
        [stage] = parse("# escape=`\nFROM python:3.12-slim\nRUN echo a `\n  b\n")
        assert stage.instructions[0].args == ("echo a b",)

    def test_a_json_array_is_exec_form(self) -> None:
        [stage] = parse('FROM x\nCMD ["python", "app.py"]\n')
        assert stage.instructions[0].form == "exec"
        assert stage.instructions[0].args == ("python", "app.py")

    def test_brackets_that_are_not_json_are_shell_form(self) -> None:
        """Docker runs `CMD [python, app.py]` through a shell, literally."""
        assert process("FROM x\nCMD [python, app.py]\n") == (
            "/bin/sh",
            "-c",
            "[python, app.py]",
        )

    def test_flags_are_split_off_in_order(self) -> None:
        [_, final] = parse(
            "FROM x AS build\nFROM y\nCOPY --from=build --chown=app:app /src /app\n"
        )
        copy = final.instructions[0]
        assert copy.flags == (("from", "build"), ("chown", "app:app"))
        assert copy.args == ("/src", "/app")
        assert copy.text == "COPY --from=build --chown=app:app /src /app"

    def test_keywords_and_aliases_are_case_insensitive(self) -> None:
        [build, final] = parse("from x as Build\nfrom build\n")
        assert build.name == "Build"
        assert final.base == "build"

    def test_build_arguments_resolve_in_from(self) -> None:
        [stage] = parse(
            "ARG PY=3.12\nARG FLAVOUR\nFROM python:${PY}-${FLAVOUR:-slim}\n"
        )
        assert stage.base == "python:3.12-slim"


class TestRefusals:
    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("RUN echo\n", "line 1: the first instruction must be FROM"),
            ("# only a comment\n", "has no FROM"),
            ("FROM x\nCOPPY . .\n", "line 2: unknown instruction 'COPPY'"),
            ("FROM x\nRUN <<EOF\necho\nEOF\n", "line 2: heredocs"),
            ("FROM x\nCMD\n", "line 2: CMD needs a command"),
            ("ARG BASE\nFROM ${BASE}\n", "names no image"),
            ("FROM x y z\n", "FROM takes an image"),
            ("# escape=x\nFROM x\n", "escape directive"),
        ],
    )
    def test_a_file_the_builder_would_refuse(self, text: str, message: str) -> None:
        with pytest.raises(DockerfileError, match=message):
            parse(text)


class TestComposingTheProcess:
    def test_entrypoint_then_cmd(self) -> None:
        assert process('FROM x\nENTRYPOINT ["gunicorn"]\nCMD ["app:app"]\n') == (
            "gunicorn",
            "app:app",
        )

    def test_a_shell_entrypoint_ignores_cmd(self) -> None:
        assert process('FROM x\nENTRYPOINT gunicorn app:app\nCMD ["ignored"]\n') == (
            "/bin/sh",
            "-c",
            "gunicorn app:app",
        )

    def test_an_entrypoint_resets_an_inherited_cmd(self) -> None:
        text = 'FROM x AS base\nCMD ["old"]\nFROM base\nENTRYPOINT ["new"]\n'
        assert process(text) == ("new",)

    def test_a_cmd_this_stage_set_survives_a_later_entrypoint(self) -> None:
        text = 'FROM x\nCMD ["--flag"]\nENTRYPOINT ["prog"]\n'
        assert process(text) == ("prog", "--flag")

    def test_cmd_is_inherited_from_an_earlier_stage(self) -> None:
        assert process('FROM x AS base\nCMD ["python"]\nFROM base\n') == ("python",)

    def test_a_numbered_stage_is_an_earlier_stage(self) -> None:
        assert process('FROM x\nCMD ["python"]\nFROM 0\n') == ("python",)

    def test_shell_changes_what_runs_the_shell_form(self) -> None:
        text = 'FROM x\nSHELL ["/bin/ash", "-eo", "pipefail", "-c"]\nCMD run.sh\n'
        assert process(text) == ("/bin/ash", "-eo", "pipefail", "-c", "run.sh")

    def test_no_cmd_is_no_process(self) -> None:
        assert process("FROM python:3.12-slim\n") == ()

    def test_the_user_follows_build_arguments(self) -> None:
        stages = parse("FROM x AS base\nARG UID=10001\nUSER ${UID}\nFROM base\n")
        assert lineage(stages).user == "10001"


class TestWhatPid1Becomes:
    """Measured on python:3.12-slim (dash 0.5.12) and its bash 5.2."""

    @pytest.mark.parametrize(
        ("cmd", "pid1"),
        [
            ("CMD python w.py", "/bin/sh"),
            ('CMD ["sh", "-c", "python w.py"]', "sh"),
            ('CMD ["sh", "-c", "true && python w.py"]', "sh"),
            ("CMD exec python w.py", "python"),
            ('CMD ["sh", "-c", "true && exec python w.py"]', "python"),
            ('CMD ["bash", "-c", "python w.py"]', "python"),
            ('CMD ["bash", "-c", "true && python w.py"]', "python"),
            ('CMD ["/bin/bash", "-c", "python w.py | tee log"]', "/bin/bash"),
            ('CMD ["sh", "-c", "exec python $APP"]', "sh"),
            ('CMD ["sh", "-c", "exec"]', "sh"),
            ('CMD ["sh", "-c", "exec python \'w.py"]', "sh"),
            ('CMD ["zsh", "-c", "python w.py"]', "zsh"),
        ],
    )
    def test_pid1(self, cmd: str, pid1: str) -> None:
        assert process(f"FROM x\n{cmd}\n")[0] == pid1
