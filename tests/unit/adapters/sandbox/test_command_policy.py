"""The gate between a typed line and a running process.

The rule these tests exist to protect is PLAN.md §5.3's: the policy a reference
solution is validated against in CI must be byte-for-byte the policy a solver's
input is executed against. The mechanism is that both go through
`practice.domain.commands`, and the test that proves it is
`test_it_does_not_reimplement_parsing` below — everything else here is about the
allowlist and the shape of the refusals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.sandbox.command_policy import CommandPolicy, CommandRejectedError
from practice.domain.commands import SHELL_METACHARACTERS, parse_command_line
from practice.domain.exercise import (
    CheckSpec,
    Difficulty,
    Exercise,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
    KataSpec,
)
from practice.domain.ids import ExerciseId, tag
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from practice.domain.exercise import ExerciseSpec


def a_scenario_spec() -> GitScenarioSpec:
    return GitScenarioSpec(
        fixture="fixture.sh",
        reference="solution.cmds",
        checks=(
            CheckSpec(
                id="history-preserved",
                label="The bad commit is still reachable",
                severity=Severity.REQUIRED,
                assertion="is_ancestor",
            ),
        ),
        allowed_commands=frozenset({"git", "cat", "write"}),
    )


def an_exercise(spec: ExerciseSpec) -> Exercise:
    kind = (
        ExerciseKind.KATA if isinstance(spec, KataSpec) else ExerciseKind.GIT_SCENARIO
    )
    return Exercise(
        id=ExerciseId("git/undo-a-commit"),
        kind=kind,
        title="Undo a commit",
        prompt="Undo it without rewriting published history.",
        difficulty=Difficulty.MEDIUM,
        tags=(tag("history"),),
        estimated_minutes=10,
        hints=(Hint("What does your teammate already have?"),),
        notes="Why revert and not reset.",
        spec=spec,
    )


@pytest.fixture
def policy() -> CommandPolicy:
    return CommandPolicy.for_spec(a_scenario_spec())


# --- where the allowlist comes from ----------------------------------------


def test_it_reads_the_allowlist_from_the_exercise() -> None:
    policy = CommandPolicy.for_exercise(an_exercise(a_scenario_spec()))

    assert policy.allowed == frozenset({"git", "cat", "write"})


def test_a_kata_permits_nothing() -> None:
    """Not a special case here, which is the point.

    `AttemptPolicy.for_exercise` already decided that a kata has no command
    console and therefore no permitted commands. Restating that rule in this
    adapter would be a second chance to get it wrong — so the test asserts the
    adapter inherits it rather than implements it.
    """
    kata = an_exercise(
        KataSpec(
            language="python", stub="stub.py", tests="tests.py", reference="solution.py"
        )
    )

    policy = CommandPolicy.for_exercise(kata)

    assert policy.allowed == frozenset()
    with pytest.raises(CommandRejectedError):
        policy.vet(["git", "status"])


# --- parsing ---------------------------------------------------------------


def test_it_parses_a_line_into_an_argv(policy: CommandPolicy) -> None:
    assert policy.vet_line('git commit -m "a message"') == (
        "git",
        "commit",
        "-m",
        "a message",
    )


def test_it_does_not_reimplement_parsing(policy: CommandPolicy) -> None:
    """The PLAN.md §5.3 guarantee, asserted directly.

    Two implementations of "what is a legal command line" would let a scenario
    ship whose `solution.cmds` passes content validation and cannot be typed by
    the solver. So this compares the policy's answer against the domain
    function that the content validator also calls, rather than against a
    literal — a second copy would pass a literal-based test perfectly.
    """
    line = "git  log   --oneline --decorate"

    assert policy.vet_line(line) == parse_command_line(line)


@pytest.mark.parametrize("character", sorted(SHELL_METACHARACTERS))
def test_every_shell_character_is_refused(
    policy: CommandPolicy, character: str
) -> None:
    """Parametrized over the domain's own set, so a character added there is
    covered here without anyone remembering to add a case.
    """
    with pytest.raises(CommandRejectedError):
        policy.vet_line(f"git log {character} cat")


def test_a_redirection_is_refused_with_the_remedy(policy: CommandPolicy) -> None:
    """The reason the rejection exists at all.

    There is no shell, so `write x > f` could not redirect — and the failure to
    avoid is the silent one, where the command appears to work and the file does
    not change. The message names the virtual commands that do the job.
    """
    with pytest.raises(CommandRejectedError) as raised:
        policy.vet_line("write notes.md > out.txt")

    assert "write" in raised.value.reason
    assert "append" in raised.value.reason


def test_an_unbalanced_quote_is_refused(policy: CommandPolicy) -> None:
    with pytest.raises(CommandRejectedError):
        policy.vet_line('git commit -m "unfinished')


def test_a_blank_line_is_not_a_command(policy: CommandPolicy) -> None:
    with pytest.raises(CommandRejectedError):
        policy.vet_line("   ")


# --- the allowlist ---------------------------------------------------------


def test_an_allowed_program_passes(policy: CommandPolicy) -> None:
    policy.vet(["git", "status"])


def test_a_disallowed_program_is_refused(policy: CommandPolicy) -> None:
    with pytest.raises(CommandRejectedError) as raised:
        policy.vet(["curl", "https://example.invalid"])

    assert "'curl' is not allowed" in raised.value.reason


def test_a_refusal_lists_what_is_allowed(policy: CommandPolicy) -> None:
    """A refusal that does not say what *would* work is a refusal the solver
    will make again.
    """
    with pytest.raises(CommandRejectedError) as raised:
        policy.vet(["rm", "-rf", "."])

    assert "cat, git, write" in raised.value.reason


def test_a_refusal_carries_what_was_typed(policy: CommandPolicy) -> None:
    """So the caller can echo it back next to the reason."""
    with pytest.raises(CommandRejectedError) as raised:
        policy.vet_line("curl example.invalid")

    assert raised.value.typed == "curl example.invalid"


def test_an_empty_argv_is_refused(policy: CommandPolicy) -> None:
    with pytest.raises(CommandRejectedError):
        policy.vet([])


def test_the_allowlist_is_matched_on_the_program_only(policy: CommandPolicy) -> None:
    """Arguments are not inspected. Grading what a command *did* is the whole
    thesis (PLAN.md §1) — an allowlist that tried to judge arguments would be
    the string matching the project exists to reject.
    """
    policy.vet(["git", "push", "--force", "origin", "main"])


def test_an_empty_allowlist_lists_itself_readably() -> None:
    assert CommandPolicy(allowed=frozenset()).listing == "(none)"
