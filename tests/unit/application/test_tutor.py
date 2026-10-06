"""The two renderings of a tutor context: the Markdown and the JSON.

Contexts are built by hand here rather than through `ExportTutorContext`. That
use case's own tests hold it to what it leaves out; these are about what the
text says for a context that is already decided, and a renderer test that went
through the use case would be testing two things and naming one.

The repository is the exception, and comes from `view_of` over the fake
builder: a `RepoView` holds a laid-out graph, and writing one out by hand would
be a second, worse `lay_out`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime

from practice.application.dto import RepoView, TutorContext
from practice.application.tutor import TUTOR_PROMPT, as_json, render_markdown
from practice.application.use_cases.inspect_repository import view_of
from practice.domain.attempt import (
    AttemptMode,
    AttemptStatus,
    CommandResult,
    CommandRun,
    HintRevealed,
)
from practice.domain.exercise import Difficulty, ExerciseKind, Hint
from practice.domain.ids import ExerciseId
from practice.domain.verdict import CheckReport, Severity, Verdict
from tests.fakes import RepoBuilder, a_repo

AT = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def a_context() -> TutorContext:
    """An open scenario with nothing done in it yet."""
    return TutorContext(
        exercise_id=ExerciseId("git/revert-a-pushed-commit"),
        title="Revert a pushed commit",
        kind=ExerciseKind.GIT_SCENARIO,
        difficulty=Difficulty.MEDIUM,
        prompt="Undo it without rewriting published history.",
        status=AttemptStatus.ACTIVE,
        mode=AttemptMode.PRACTICE,
        allowed_commands=("cat", "git"),
        commands_left=25,
        hints_left=3,
    )


def a_kata_context() -> TutorContext:
    return replace(
        a_context(),
        exercise_id=ExerciseId("katas/two-sum"),
        title="Two Sum",
        kind=ExerciseKind.KATA,
        difficulty=Difficulty.EASY,
        allowed_commands=(),
        commands_left=0,
        hints_left=1,
    )


def a_command(
    line: str,
    *,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    truncated: bool = False,
) -> CommandRun:
    return CommandRun(
        at=AT,
        argv=tuple(line.split()),
        result=CommandResult(
            exit_code=exit_code, stdout=stdout, stderr=stderr, truncated=truncated
        ),
    )


def a_view(repo: RepoBuilder) -> RepoView:
    return view_of(repo.build())


def a_published_repo() -> RepoBuilder:
    """Two commits, with `main` one ahead of `origin/main` and HEAD on it."""
    repo = a_repo()
    first, second = repo.chain("skeleton", "bad refactor")
    repo.branch("main", second).remote("main", first).head("refs/heads/main")
    return repo


# --- markdown: the frame ----------------------------------------------------


def test_the_prompt_comes_first() -> None:
    """Before anything a model could mistake for the question."""
    assert render_markdown(a_context()).startswith(TUTOR_PROMPT)


def test_the_prompt_refuses_the_solution_even_when_asked() -> None:
    """The one rule a solver will test, so the one worth pinning the words of."""
    assert "even if I ask for it" in TUTOR_PROMPT


def test_the_summary_names_the_exercise_and_the_state_of_the_attempt() -> None:
    text = render_markdown(a_context())

    assert "# Revert a pushed commit" in text
    assert "- Exercise: `git/revert-a-pushed-commit` (git scenario, medium)" in text
    assert "- Attempt: active, practice mode" in text
    assert "- Hints: 0 revealed, 3 not yet revealed" in text


def test_a_scenario_states_its_budget_and_its_allowlist() -> None:
    context = replace(a_context(), events=(a_command("git status"),), commands_left=24)

    assert "- Commands: 1 run, 24 left. Allowed: `cat`, `git`" in render_markdown(
        context
    )


def test_a_kata_has_no_commands_line_at_all() -> None:
    """ "0 run, 0 left" is true of a kata and reads as a budget that was spent."""
    assert "- Commands:" not in render_markdown(a_kata_context())


def test_the_task_keeps_its_own_whitespace() -> None:
    """Prompts are authored as aligned block text, so they go in a fence."""
    context = replace(a_context(), prompt="nums   = [2, 7]\ntarget = 9\n")

    assert "```text\nnums   = [2, 7]\ntarget = 9\n```" in render_markdown(context)


# --- markdown: the history --------------------------------------------------


def test_an_attempt_with_nothing_done_says_so() -> None:
    assert "## What I have done so far\n\nNothing yet." in render_markdown(a_context())


def test_a_command_is_shown_with_its_exit_code_and_its_output() -> None:
    context = replace(
        a_context(),
        events=(a_command("git status", stdout="On branch main\n"),),
    )

    text = render_markdown(context)

    assert "**1.** Ran `git status` (exit 0)" in text
    assert "stdout:\n\n```text\nOn branch main\n```" in text
    assert "stderr:" not in text


def test_a_failing_command_shows_what_it_wrote_to_stderr() -> None:
    """Often the most instructive thing in the attempt, and the reason a tutor
    is being asked at all.
    """
    context = replace(
        a_context(),
        events=(
            a_command(
                "git revert HEAD",
                exit_code=1,
                stdout="Auto-merging parser.py\n",
                stderr="error: could not revert\n",
            ),
        ),
    )

    text = render_markdown(context)

    assert "(exit 1)" in text
    assert "stdout:\n\n```text\nAuto-merging parser.py\n```" in text
    assert "stderr:\n\n```text\nerror: could not revert\n```" in text


def test_a_command_that_printed_nothing_says_so() -> None:
    """An empty fence reads as output that went missing."""
    text = render_markdown(replace(a_context(), events=(a_command("git add ."),)))

    assert "It printed nothing." in text
    assert "```text\n\n```" not in text


def test_truncated_output_is_flagged() -> None:
    context = replace(
        a_context(),
        events=(a_command("git log", stdout="commit 1a2b\n", truncated=True),),
    )

    assert "The tool cut this output short" in render_markdown(context)


def test_untruncated_output_is_not() -> None:
    context = replace(a_context(), events=(a_command("git log", stdout="commit\n"),))

    assert "cut this output short" not in render_markdown(context)


def test_a_revealed_hint_is_numbered_in_sequence_and_by_its_own_position() -> None:
    """Two numbers: where it fell in the attempt, and which hint it was."""
    context = replace(
        a_context(),
        events=(
            a_command("git status"),
            HintRevealed(at=AT, index=0, hint=Hint("Read the build script.")),
        ),
        hints_left=2,
    )

    text = render_markdown(context)

    assert "**2.** Revealed hint 1: Read the build script." in text
    assert "- Hints: 1 revealed, 2 not yet revealed" in text


def test_output_holding_a_fence_gets_a_longer_one() -> None:
    """`git show` on a README does this. Three backticks around three backticks
    ends the block early and turns the rest of the transcript into prose.
    """
    readme = "Usage:\n```\npractice up\n```\n"
    context = replace(a_context(), events=(a_command("cat README.md", stdout=readme),))

    text = render_markdown(context)

    assert f"````text\n{readme.rstrip()}\n````" in text


# --- markdown: the repository -----------------------------------------------


def test_the_repository_reads_in_the_order_the_panel_does() -> None:
    context = replace(a_context(), repo=a_view(a_published_repo()))

    text = render_markdown(context)

    head = text.index("- HEAD:")
    worktree = text.index("- Worktree")
    branches = text.index("- Branches:")
    stash = text.index("- Stash:")
    history = text.index("History, newest first")
    assert head < worktree < branches < stash < history


def test_head_on_a_branch_names_the_branch_and_the_commit() -> None:
    repo = a_published_repo()
    view = a_view(repo)
    assert view.head_sha is not None

    text = render_markdown(replace(a_context(), repo=view))

    assert f"- HEAD: `main` at `{view.head_sha.short}`" in text


def test_a_detached_head_is_said_out_loud() -> None:
    repo = a_repo()
    first, second = repo.chain("skeleton", "bad refactor")
    repo.branch("main", second).detach(first)

    text = render_markdown(replace(a_context(), repo=a_view(repo)))

    assert f"- HEAD: detached at `{first.short}`" in text


def test_an_unborn_branch_is_said_out_loud() -> None:
    repo = a_repo().head("refs/heads/main")

    text = render_markdown(replace(a_context(), repo=a_view(repo)))

    assert "- HEAD: `main`, unborn (no commit on it yet)" in text
    assert "- no commits" in text


def test_a_clean_worktree_is_one_line() -> None:
    text = render_markdown(replace(a_context(), repo=a_view(a_published_repo())))

    assert "- Worktree: clean" in text


def test_a_dirty_worktree_keeps_its_four_states_apart() -> None:
    """Four problems with four fixes, and a conflict is the one worth asking
    a tutor about.
    """
    repo = a_published_repo()
    repo.status(
        staged=["b.py", "a.py"],
        unstaged=["c.py"],
        untracked=["scratch.txt"],
        unmerged=["parser.py"],
    )

    text = render_markdown(replace(a_context(), repo=a_view(repo)))

    assert "- Worktree, unmerged: `parser.py`" in text
    assert "- Worktree, staged: `a.py`, `b.py`" in text
    assert "- Worktree, modified, not staged: `c.py`" in text
    assert "- Worktree, untracked: `scratch.txt`" in text
    assert "- Worktree: clean" not in text


def test_refs_are_listed_by_kind_with_what_they_point_at() -> None:
    repo = a_published_repo()
    view = a_view(repo)
    first = view.remote_branches["refs/remotes/origin/main"]

    text = render_markdown(replace(a_context(), repo=view))

    assert f"- Remote branches: `origin/main` at `{first.short}`" in text
    assert "- Tags: none" in text


def test_stash_messages_are_listed_and_an_empty_stash_says_empty() -> None:
    stashed = a_published_repo()
    stashed.stash("WIP on main: the fix I forgot about")

    assert "- Stash: WIP on main: the fix I forgot about" in render_markdown(
        replace(a_context(), repo=a_view(stashed))
    )
    assert "- Stash: empty" in render_markdown(
        replace(a_context(), repo=a_view(a_published_repo()))
    )


def test_each_commit_names_what_points_at_it_and_what_it_was_built_on() -> None:
    """HEAD is marked on its commit, and the parents are written out because a
    list is not a drawing: two interleaved branches look like one without them.
    """
    repo = a_repo()
    first, second = repo.chain("skeleton", "bad refactor")
    repo.branch("main", second).remote("main", first).head("refs/heads/main")

    text = render_markdown(replace(a_context(), repo=a_view(repo)))

    assert (
        f"- `{second.short}` (HEAD, main) bad refactor [parents: {first.short}]" in text
    )
    assert f"- `{first.short}` (origin/main) skeleton [parents: none]" in text


def test_a_merge_lists_both_parents_and_an_unlabelled_commit_has_no_brackets() -> None:
    repo = a_repo()
    base = repo.commit("base")
    left = repo.commit("left", parents=[base])
    right = repo.commit("right", parents=[base])
    merge = repo.commit("merge", parents=[left, right])
    repo.branch("main", merge).head("refs/heads/main")

    text = render_markdown(replace(a_context(), repo=a_view(repo)))

    assert f"[parents: {left.short}, {right.short}]" in text
    assert f"- `{left.short}` left [parents: {base.short}]" in text


def test_a_scenario_with_no_repository_says_where_it_went() -> None:
    text = render_markdown(a_context())

    assert "## The repository right now" in text
    assert "no longer on disk" in text


def test_a_kata_has_no_repository_section() -> None:
    assert "The repository" not in render_markdown(a_kata_context())


# --- markdown: source, verdict, notes ---------------------------------------


def test_the_source_is_fenced_in_its_own_language() -> None:
    context = replace(
        a_kata_context(), source="def two_sum():\n    ...\n", language="python"
    )

    text = render_markdown(context)

    assert "## My solution as it stands" in text
    assert "```python\ndef two_sum():\n    ...\n```" in text


def test_a_context_with_no_source_has_no_solution_section() -> None:
    assert "My solution" not in render_markdown(a_context())


def a_mixed_verdict() -> Verdict:
    return Verdict(
        reports=(
            CheckReport(
                check_id="tree-restored",
                label="The working parser is back.",
                severity=Severity.REQUIRED,
                passed=True,
                explanation="Why this check exists.",
            ),
            CheckReport(
                check_id="history-preserved",
                label="The bad commit is still reachable.",
                severity=Severity.REQUIRED,
                passed=False,
                expected="an ancestor of main",
                actual="not reachable",
                explanation="Published history is not yours to rewrite.",
            ),
            CheckReport(
                check_id="no-force-push",
                label="Did not force-push.",
                severity=Severity.ADVISORY,
                passed=False,
            ),
        )
    )


def test_the_verdict_shows_what_the_verdict_page_shows() -> None:
    context = replace(
        a_context(), status=AttemptStatus.COMPLETED, verdict=a_mixed_verdict()
    )

    text = render_markdown(context)

    assert "Outcome: fail (1 of 3 checks passed)" in text
    assert "- Passed: The working parser is back." in text
    assert (
        "- Failed: The bad commit is still reachable. Expected an ancestor of "
        "main, got not reachable. Published history is not yours to rewrite." in text
    )
    assert "- Advisory, not met: Did not force-push." in text


def test_a_passing_checks_explanation_is_not_printed() -> None:
    """The page's rule: an explanation is shown for a check that was not met.
    For one that passed, the solver has never been told why it exists.
    """
    context = replace(
        a_context(), status=AttemptStatus.COMPLETED, verdict=a_mixed_verdict()
    )

    assert "Why this check exists." not in render_markdown(context)


def test_an_open_attempt_has_no_verdict_or_notes_section() -> None:
    text = render_markdown(a_context())

    assert "## The verdict" not in text
    assert "## The author's notes" not in text


def test_the_notes_come_last() -> None:
    context = replace(
        a_context(),
        status=AttemptStatus.COMPLETED,
        verdict=a_mixed_verdict(),
        notes="Why revert and not reset.\n",
    )

    assert render_markdown(context).endswith(
        "## The author's notes\n\nWhy revert and not reset.\n"
    )


# --- json -------------------------------------------------------------------


def test_the_json_is_plain_data_that_serialises_without_help() -> None:
    """No enum, no `Sha`, no frozenset: a caller must not need a `default=`."""
    context = replace(
        a_context(),
        events=(
            a_command("git status", stdout="On branch main\n"),
            HintRevealed(at=AT, index=0, hint=Hint("Read the build script.")),
        ),
        repo=a_view(a_published_repo()),
        status=AttemptStatus.COMPLETED,
        verdict=a_mixed_verdict(),
        notes="Why revert and not reset.",
    )

    assert json.loads(json.dumps(as_json(context))) == as_json(context)


def test_the_json_carries_the_prompt_the_exercise_and_the_attempt() -> None:
    data = as_json(a_context())

    assert data["tutor_prompt"] == TUTOR_PROMPT
    assert data["exercise"] == {
        "id": "git/revert-a-pushed-commit",
        "title": "Revert a pushed commit",
        "kind": "git_scenario",
        "difficulty": "medium",
        "prompt": "Undo it without rewriting published history.",
    }
    assert data["attempt"] == {
        "status": "active",
        "mode": "practice",
        "allowed_commands": ["cat", "git"],
        "commands_left": 25,
        "hints_left": 3,
    }


def test_the_json_keeps_the_two_kinds_of_event_apart() -> None:
    context = replace(
        a_context(),
        events=(
            a_command("git revert HEAD", exit_code=1, stderr="conflict\n"),
            HintRevealed(at=AT, index=1, hint=Hint("What does your teammate have?")),
        ),
    )

    assert as_json(context)["events"] == [
        {
            "type": "command",
            "command": "git revert HEAD",
            "exit_code": 1,
            "stdout": "",
            "stderr": "conflict\n",
            "truncated": False,
        },
        {"type": "hint", "number": 2, "text": "What does your teammate have?"},
    ]


def test_an_open_context_has_null_where_nothing_exists_yet() -> None:
    data = as_json(a_context())

    assert data["repository"] is None
    assert data["source"] is None
    assert data["verdict"] is None
    assert data["notes"] is None


def test_the_json_repository_is_ordered_and_uses_short_ref_names() -> None:
    repo = a_repo()
    first, second = repo.chain("skeleton", "bad refactor")
    repo.branch("main", second).remote("main", first).head("refs/heads/main")
    repo.status(staged=["b.py", "a.py"])
    repo.stash("WIP on main")

    data = as_json(replace(a_context(), repo=a_view(repo)))["repository"]

    assert data == {
        "head": {"branch": "main", "sha": second.value, "detached": False},
        "worktree": {
            "unmerged": [],
            "staged": ["a.py", "b.py"],
            "unstaged": [],
            "untracked": [],
        },
        "branches": {"main": second.value},
        "remote_branches": {"origin/main": first.value},
        "tags": {},
        "stashes": ["WIP on main"],
        "history": [
            {
                "sha": second.value,
                "subject": "bad refactor",
                "parents": [first.value],
                "refs": ["main"],
            },
            {
                "sha": first.value,
                "subject": "skeleton",
                "parents": [],
                "refs": ["origin/main"],
            },
        ],
    }


def test_the_json_head_of_an_unborn_branch_has_no_sha() -> None:
    data = as_json(replace(a_context(), repo=a_view(a_repo().head("refs/heads/main"))))

    assert data["repository"] is not None
    assert json.loads(json.dumps(data))["repository"]["head"] == {
        "branch": "main",
        "sha": None,
        "detached": False,
    }


def test_the_json_source_carries_its_language() -> None:
    context = replace(a_kata_context(), source="def two_sum(): ...", language="python")

    assert as_json(context)["source"] == {
        "language": "python",
        "text": "def two_sum(): ...",
    }


def test_the_json_verdict_withholds_a_passing_checks_explanation_too() -> None:
    """The same rule as the Markdown, so the two cannot disagree about what a
    solver has been told.
    """
    context = replace(
        a_context(), status=AttemptStatus.COMPLETED, verdict=a_mixed_verdict()
    )

    assert as_json(context)["verdict"] == {
        "outcome": "fail",
        "checks": [
            {
                "label": "The working parser is back.",
                "severity": "required",
                "passed": True,
                "expected": None,
                "actual": None,
                "explanation": None,
            },
            {
                "label": "The bad commit is still reachable.",
                "severity": "required",
                "passed": False,
                "expected": "an ancestor of main",
                "actual": "not reachable",
                "explanation": "Published history is not yours to rewrite.",
            },
            {
                "label": "Did not force-push.",
                "severity": "advisory",
                "passed": False,
                "expected": None,
                "actual": None,
                "explanation": None,
            },
        ],
    }
