"""The seven assertions over what an image is built from and what it runs.

The case worth reading first is `TestPid1Matches::test_sh_dash_c_in_brackets
_is_still_a_shell`: the exec form with a shell in it is the counter-example a
text match on `CMD [` would pass, and the reason the port composes the process
rather than handing back the instruction.
"""

from __future__ import annotations

from tests.fakes.build import FakeBuildQuery, a_stage, exec_form, shell_form
from tests.unit.domain.containers.helpers import run

GOOD = a_stage(
    "python:3.12-slim",
    exec_form("COPY", "requirements.txt", ".", at=3),
    shell_form("RUN", "pip install -r requirements.txt", at=4),
    exec_form("COPY", ".", ".", at=5),
    exec_form("CMD", "python", "app.py", at=6),
)

BUILDER = a_stage("golang:1.23", shell_form("RUN", "go build"), name="build")


class TestBaseImageMatches:
    def test_passes_a_pinned_base(self) -> None:
        image = FakeBuildQuery(stages=[GOOD])
        report = run("base_image_matches", image, pattern=r"^python:3\.\d+-slim$")
        assert report.passed
        assert report.actual == "FROM python:3.12-slim"

    def test_fails_latest(self) -> None:
        image = FakeBuildQuery(stages=[a_stage("python:latest")])
        assert not run("base_image_matches", image, pattern=r"-slim$").passed

    def test_reads_the_final_stage_by_default(self) -> None:
        image = FakeBuildQuery(stages=[BUILDER, GOOD])
        assert run("base_image_matches", image, pattern="^python").passed

    def test_reads_a_named_stage_when_asked(self) -> None:
        image = FakeBuildQuery(stages=[BUILDER, GOOD])
        report = run("base_image_matches", image, pattern="^golang", stage="build")
        assert report.passed
        assert report.expected == (
            "stage 'build' built FROM an image matching '^golang'"
        )

    def test_a_stage_that_does_not_exist_fails(self) -> None:
        image = FakeBuildQuery(stages=[GOOD])
        report = run("base_image_matches", image, pattern=".", stage="build")
        assert not report.passed
        assert report.actual == "<no such stage>"

    def test_a_file_with_no_from_fails(self) -> None:
        report = run("base_image_matches", FakeBuildQuery(), pattern=".")
        assert report.actual == "<the file has no FROM>"

    def test_an_unreadable_definition_says_so(self) -> None:
        report = run("base_image_matches", FakeBuildQuery(error="bad"), pattern=".")
        assert report.actual == "<no definition could be read>"


class TestOrderedBefore:
    def test_dependencies_before_source_passes(self) -> None:
        report = run(
            "ordered_before",
            FakeBuildQuery(stages=[GOOD]),
            first="^RUN .*pip install",
            then=r"^COPY \. ",
        )
        assert report.passed
        assert report.actual == (
            "'RUN pip install -r requirements.txt' is instruction 2, "
            "'COPY . .' is instruction 3"
        )

    def test_source_before_dependencies_fails(self) -> None:
        report = run(
            "ordered_before",
            FakeBuildQuery(stages=[GOOD]),
            first=r"^COPY \. ",
            then="^RUN .*pip install",
        )
        assert not report.passed

    def test_a_missing_then_fails_rather_than_passing_vacuously(self) -> None:
        report = run(
            "ordered_before",
            FakeBuildQuery(stages=[GOOD]),
            first="^COPY",
            then="^RUN .*npm",
        )
        assert not report.passed
        assert report.actual == "no instruction matches '^RUN .*npm'"

    def test_a_missing_first_fails(self) -> None:
        report = run(
            "ordered_before", FakeBuildQuery(stages=[GOOD]), first="^ADD", then="^RUN"
        )
        assert report.actual == "no instruction matches '^ADD'"

    def test_no_stage_fails(self) -> None:
        report = run("ordered_before", FakeBuildQuery(), first="a", then="b")
        assert not report.passed


class TestPid1Matches:
    def test_an_exec_form_program_is_pid1(self) -> None:
        image = FakeBuildQuery(process=["python", "app.py"])
        report = run("pid1_matches", image, pattern="(^|/)(ba|da)?sh$", negated=True)
        assert report.passed
        assert report.actual == "PID 1 is 'python', started as 'python app.py'"

    def test_a_shell_form_is_a_shell(self) -> None:
        image = FakeBuildQuery(process=["/bin/sh", "-c", "python app.py"])
        report = run("pid1_matches", image, pattern="(^|/)(ba|da)?sh$", negated=True)
        assert not report.passed

    def test_sh_dash_c_in_brackets_is_still_a_shell(self) -> None:
        image = FakeBuildQuery(process=["sh", "-c", "python worker.py"])
        assert run("pid1_matches", image, pattern="(^|/)(ba|da)?sh$").passed

    def test_no_process_fails(self) -> None:
        report = run("pid1_matches", FakeBuildQuery(), pattern=".")
        assert report.actual == "<nothing sets a CMD or ENTRYPOINT>"

    def test_no_definition_fails(self) -> None:
        report = run("pid1_matches", FakeBuildQuery(error="bad"), pattern=".")
        assert report.actual == "<no definition could be read>"


class TestCommandMatches:
    BIND = r"(--bind[= ]|-b )0\.0\.0\.0:8000"

    def test_a_public_bind_passes(self) -> None:
        image = FakeBuildQuery(
            process=["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
        )
        assert run("command_matches", image, pattern=self.BIND).passed

    def test_the_default_bind_fails(self) -> None:
        image = FakeBuildQuery(process=["gunicorn", "app:app"])
        report = run("command_matches", image, pattern=self.BIND)
        assert not report.passed
        assert report.actual == "the container starts 'gunicorn app:app'"

    def test_no_process_fails(self) -> None:
        assert not run("command_matches", FakeBuildQuery(), pattern=".").passed


class TestRunsAs:
    ROOT = "^(root|0)(:|$)"

    def test_root_by_default(self) -> None:
        report = run("runs_as", FakeBuildQuery(stages=[GOOD]), pattern=self.ROOT)
        assert report.passed
        assert report.actual == "it runs as 'root'"

    def test_a_named_user_is_not_root(self) -> None:
        image = FakeBuildQuery(stages=[GOOD], user="app")
        assert run("runs_as", image, pattern=self.ROOT, negated=True).passed

    def test_no_definition_fails(self) -> None:
        image = FakeBuildQuery(error="bad")
        assert not run("runs_as", image, pattern=self.ROOT).passed


class TestInstructionMatches:
    def test_reports_the_line_that_matched(self) -> None:
        report = run(
            "instruction_matches", FakeBuildQuery(stages=[GOOD]), pattern="^RUN pip"
        )
        assert report.passed
        assert report.actual == "line 4: 'RUN pip install -r requirements.txt'"

    def test_negated_it_rules_a_line_out(self) -> None:
        stage = a_stage("python:3.12-slim", shell_form("RUN", "rm -f .env"))
        report = run(
            "instruction_matches",
            FakeBuildQuery(stages=[stage]),
            pattern=r"^RUN .*rm .*\.env",
            negated=True,
        )
        assert not report.passed

    def test_nothing_matching_fails(self) -> None:
        report = run(
            "instruction_matches", FakeBuildQuery(stages=[GOOD]), pattern="HEALTHCHECK"
        )
        assert report.actual == "no instruction in the final stage matches"

    def test_no_stage_fails(self) -> None:
        assert not run("instruction_matches", FakeBuildQuery(), pattern=".").passed


class TestPathInImage:
    def test_a_copied_file_is_in_the_image(self) -> None:
        report = run("path_in_image", FakeBuildQuery(in_image=[".env"]), path=".env")
        assert report.passed
        assert report.actual == ".env is copied into a layer of the image"

    def test_negated_it_keeps_a_secret_out(self) -> None:
        report = run("path_in_image", FakeBuildQuery(), path=".env", negated=True)
        assert report.passed

    def test_no_definition_fails(self) -> None:
        report = run("path_in_image", FakeBuildQuery(error="bad"), path=".env")
        assert report.actual == "<no definition could be read>"


def test_a_long_instruction_is_quoted_short() -> None:
    long_line = "pip install " + " ".join(f"package-{n}" for n in range(40))
    stage = a_stage("python:3.12-slim", shell_form("RUN", long_line))
    report = run("instruction_matches", FakeBuildQuery(stages=[stage]), pattern="pip")
    assert report.actual is not None
    assert report.actual.endswith("...'")
    assert len(report.actual) < 120
