"""`ParsedBuildQuery`: where context files land, and the grader over a real directory.

The case worth reading first is
`test_a_builder_that_deletes_hands_a_final_stage_nothing`. It is a correct
answer to the secrets exercise that an earlier version of the layer model
failed. That is the one thing a grader must not do, and the honesty tier
confirms against a real build that the image really is clean.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.container import (
    DEFINITION_CHECK_ID,
    ContainerGrader,
    ContainerGraderError,
    ParsedBuildQuery,
    context_files,
)
from practice.domain.attempt import Attempt, AttemptPolicy
from practice.domain.exercise import CheckSpec
from practice.domain.ids import AttemptId
from practice.domain.verdict import Severity
from tests.fakes import FakeClock, FakeWorkspace, a_container, a_drill

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise

CONTEXT = {
    "app.py": "",
    "pricing.py": "",
    ".env": "KEY=1",
    "pkg/__init__.py": "",
    "pkg/models.py": "",
    "docs/a.md": "",
}


def query(dockerfile: str, context: dict[str, str] | None = None) -> ParsedBuildQuery:
    return ParsedBuildQuery(
        context=CONTEXT if context is None else context,
        editable="Dockerfile",
        source=dockerfile,
    )


class TestPathInImage:
    @pytest.mark.parametrize(
        ("dockerfile", "path", "present"),
        [
            ("FROM x\nCOPY . .\n", ".env", True),
            ("FROM x\nCOPY . /app/\n", "pkg/models.py", True),
            ("FROM x\nCOPY app.py pricing.py ./\n", ".env", False),
            ("FROM x\nCOPY app.py pricing.py ./\n", "pricing.py", True),
            ("FROM x\nCOPY pkg /app/pkg\n", "pkg/models.py", True),
            ("FROM x\nCOPY pkg /app/pkg\n", "app.py", False),
            ("FROM x\nCOPY *.py /app/\n", "pricing.py", True),
            ("FROM x\nCOPY *.py /app/\n", "pkg/models.py", False),
            ('FROM x\nCOPY ["app.py", "/app/"]\n', "app.py", True),
            ("FROM x\nWORKDIR /app\nCOPY . .\nRUN rm -f .env\n", ".env", True),
            ("FROM x\nCOPY --from=python:3.12 /usr /usr\n", "app.py", False),
            ("FROM x\n", "app.py", False),
        ],
    )
    def test_landing(self, dockerfile: str, path: str, present: bool) -> None:
        assert query(dockerfile).path_in_image(path) is present

    def test_dockerignore_keeps_a_file_out_of_the_context(self) -> None:
        context = {**CONTEXT, ".dockerignore": ".env\n"}
        assert not query("FROM x\nCOPY . .\n", context).path_in_image(".env")

    def test_a_builder_that_deletes_hands_a_final_stage_nothing(self) -> None:
        dockerfile = (
            "FROM python:3.12-slim AS build\nWORKDIR /app\nCOPY . .\nRUN rm -f .env\n"
            "FROM python:3.12-slim\nCOPY --from=build /app /app\n"
        )
        built = query(dockerfile)
        assert not built.path_in_image(".env")
        assert built.path_in_image("pkg/models.py")

    def test_a_builder_that_keeps_it_hands_it_on(self) -> None:
        dockerfile = (
            "FROM python:3.12-slim AS build\nWORKDIR /app\nCOPY . .\n"
            "FROM python:3.12-slim\nCOPY --from=build /app /app\n"
        )
        assert query(dockerfile).path_in_image(".env")

    def test_a_stage_built_from_the_builder_inherits_its_layers(self) -> None:
        """`FROM build` is the builder's layers plus more, so the rm hides nothing."""
        dockerfile = (
            "FROM python:3.12-slim AS build\nWORKDIR /app\nCOPY . .\nRUN rm -f .env\n"
            "FROM build\n"
        )
        assert query(dockerfile).path_in_image(".env")

    def test_copying_one_file_out_of_a_builder(self) -> None:
        dockerfile = (
            "FROM x AS build\nWORKDIR /src\nCOPY . .\n"
            "FROM y\nCOPY --from=build /src/app.py /srv/\n"
        )
        built = query(dockerfile)
        assert built.path_in_image("app.py")
        assert not built.path_in_image(".env")

    def test_one_file_copied_to_the_workdir_is_followed_out_of_a_builder(
        self,
    ) -> None:
        """`COPY .env .` puts the file *in* `/app`, because `.` is a directory.

        The first version landed it *at* `/app`, so copying `/app/.env` out of
        the builder found nothing, and a negated check passed a leaking image.
        """
        dockerfile = (
            "FROM x AS build\nWORKDIR /app\nCOPY .env .\n"
            "FROM y\nCOPY --from=build /app/.env /app/.env\n"
        )
        assert query(dockerfile).path_in_image(".env")

    def test_rm_follows_one_file_copied_to_the_workdir(self) -> None:
        dockerfile = (
            "FROM x AS build\nWORKDIR /app\nCOPY app.py .\nCOPY .env .\n"
            "RUN rm .env\nFROM y\nCOPY --from=build /app /app\n"
        )
        built = query(dockerfile)
        assert not built.path_in_image(".env")
        assert built.path_in_image("app.py")

    @pytest.mark.parametrize("source", [".", "./", "./app", "/app/", "app"])
    def test_a_from_source_is_normalised(self, source: str) -> None:
        """Unnormalised, `.` and `./app` matched no landing and copied nothing."""
        dockerfile = (
            "FROM x AS build\nWORKDIR /app\nCOPY . .\n"
            f"FROM y\nCOPY --from=build {source} /srv/\n"
        )
        assert query(dockerfile).path_in_image("app.py")

    def test_rm_of_a_directory_removes_what_is_under_it(self) -> None:
        dockerfile = (
            "FROM x AS build\nWORKDIR /app\nCOPY . .\nRUN rm -rf docs && rm .env\n"
            "FROM y\nCOPY --from=build /app /app\n"
        )
        built = query(dockerfile)
        assert not built.path_in_image("docs/a.md")
        assert not built.path_in_image(".env")
        assert built.path_in_image("app.py")

    def test_an_unparseable_rm_leaves_the_file_visible(self) -> None:
        """The conservative direction: report a leak rather than miss one."""
        dockerfile = (
            "FROM x AS build\nWORKDIR /app\nCOPY . .\nRUN rm 'unterminated\n"
            "FROM y\nCOPY --from=build /app /app\n"
        )
        assert query(dockerfile).path_in_image(".env")


class TestTheRestOfThePort:
    def test_the_final_user(self) -> None:
        assert query("FROM x\nUSER app\n").final_user() == "app"
        assert query("FROM x\n").final_user() == "root"

    def test_an_error_is_reported_not_raised(self) -> None:
        broken = query("FROM x\nCOPPY . .\n")
        assert broken.error() == "line 2: unknown instruction 'COPPY'"
        assert broken.stages() == ()
        assert broken.final_user() == "root"
        assert not broken.path_in_image("app.py")

    def test_compose_is_read_from_the_context_beside_a_dockerfile(self) -> None:
        context = {"compose.yaml": "services:\n  api:\n    image: x\n"}
        built = query("FROM x\n", context)
        assert built.services() == frozenset({"api"})
        assert built.service("api") == {"image": "x"}
        assert built.service("db") is None

    def test_a_compose_error_is_reported(self) -> None:
        built = ParsedBuildQuery(context={}, editable="compose.yaml", source="- a\n")
        assert built.error() is not None

    def test_context_files_reads_a_directory(self, tmp_path: Path) -> None:
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "app.py").write_text("print()", encoding="utf-8")
        (tmp_path / ".env").write_bytes(b"\xff\xfe")
        files = context_files(tmp_path)
        assert set(files) == {"api/app.py", ".env"}
        assert files["api/app.py"] == "print()"


def attempt_for(exercise: Exercise, source: str | None) -> Attempt:
    clock = FakeClock()
    attempt = Attempt(
        attempt_id=AttemptId.parse("aabbccdd-0000-4000-8000-000000000001"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=clock.now(),
    )
    if source is not None:
        attempt.save_solution(source, at=clock.now())
    return attempt


def a_library(root: Path, exercise: Exercise, files: dict[str, str]) -> Path:
    """`files` as the shipped build context of `exercise`, under `root`."""
    context = root / exercise.id.value / "context"
    for name, text in files.items():
        (context / name).parent.mkdir(parents=True, exist_ok=True)
        (context / name).write_text(text, encoding="utf-8")
    return root


class TestTheGrader:
    def test_grades_the_saved_answer_over_the_shipped_context(
        self, tmp_path: Path
    ) -> None:
        exercise = a_container()
        library = a_library(tmp_path / "content", exercise, {"app.py": ""})
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # What is on disk is the provisioned stub; the attempt's answer wins.
        (workspace / "Dockerfile").write_text('FROM x\nCMD ["gunicorn"]\n', "utf-8")
        answer = 'FROM x\nCMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]\n'
        verdict = ContainerGrader(library).grade(
            exercise, FakeWorkspace(repo=workspace), attempt_for(exercise, answer)
        )
        assert verdict.passed
        assert verdict.reports[0].check_id == DEFINITION_CHECK_ID

    def test_editing_the_workspace_context_changes_nothing(
        self, tmp_path: Path
    ) -> None:
        """The first version read the context from the workspace.

        Deleting `.env` there, or adding a `.dockerignore` naming it, passed
        the secrets exercise with the stub untouched.
        """
        exercise = a_container(
            checks=(
                CheckSpec(
                    id="no-env",
                    label=".env is in no layer.",
                    severity=Severity.REQUIRED,
                    assertion="path_in_image",
                    params={"path": ".env"},
                    negated=True,
                    explanation="Layers are immutable.",
                ),
            )
        )
        library = a_library(
            tmp_path / "content", exercise, {".env": "KEY=1", "app.py": ""}
        )
        workspace = tmp_path / "ws"
        workspace.mkdir()
        (workspace / "app.py").write_text("", encoding="utf-8")
        (workspace / ".dockerignore").write_text(".env\n", encoding="utf-8")
        stub = "FROM x\nWORKDIR /app\nCOPY . .\nRUN rm -f .env\n"
        verdict = ContainerGrader(library).grade(
            exercise, FakeWorkspace(repo=workspace), attempt_for(exercise, stub)
        )
        assert not verdict.passed

    def test_a_parse_error_is_one_failure_with_the_parsers_sentence(
        self, tmp_path: Path
    ) -> None:
        exercise = a_container()
        verdict = ContainerGrader(tmp_path).grade(
            exercise,
            FakeWorkspace(repo=tmp_path),
            attempt_for(exercise, "FROM x\nCOPPY . .\n"),
        )
        definition = verdict.reports[0]
        assert not definition.passed
        assert definition.actual == "line 2: unknown instruction 'COPPY'"
        assert definition.explanation is not None
        assert len(verdict.reports) == 2

    def test_another_kind_is_refused(self, tmp_path: Path) -> None:
        exercise = a_drill()
        with pytest.raises(ContainerGraderError, match="sql_drill"):
            ContainerGrader(tmp_path).grade(
                exercise, FakeWorkspace(repo=tmp_path), attempt_for(exercise, "x")
            )

    def test_an_attempt_with_no_answer_is_refused(self, tmp_path: Path) -> None:
        exercise = a_container()
        with pytest.raises(ContainerGraderError, match="saved no answer"):
            ContainerGrader(tmp_path).grade(
                exercise, FakeWorkspace(repo=tmp_path), attempt_for(exercise, None)
            )
