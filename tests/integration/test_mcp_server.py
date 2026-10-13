"""The MCP server's tools, called by the SDK's own client over real adapters.

`build_server` is thin: three tools that each forward to a use case and turn a
refusal into a sentence. The use cases have their own unit tests. What only this
layer can show is the protocol half -- that the tools are advertised with the
schemas and annotations a client acts on, that a refusal arrives as a failed
call a model can read rather than as a crash, and that the answers come from a
real repository on disk.

**Real services, and one attempt shared by most of the file.** Every tool here
reads, which is the claim the phase rests on, so nothing these tests do can
disturb the next one -- and a shared scenario costs one fixture run instead of
one per test. The three cases that need a different attempt state build their
own. If a test here ever *did* change the shared attempt, the last test in the
file is the one that would say so.

The client is connected in-process, over the SDK's in-memory transport: a full
initialize handshake and real JSON-RPC framing, with no subprocess. The stdio
transport and the `practice mcp` command are `tests/e2e/`'s.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import anyio
import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent

from practice.application.tutor import TUTOR_PROMPT
from practice.composition import Services, build_services
from practice.config import content_root
from practice.domain.attempt import AttemptMode
from practice.domain.ids import ExerciseId
from practice.interface.mcp import SERVER_INSTRUCTIONS, SERVER_NAME, build_server

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ids import AttemptId

REVERT = ExerciseId("git/revert-a-pushed-commit")
TWO_SUM = ExerciseId("katas/two-sum")
STAIRS = ExerciseId("katas/climbing-stairs")

TOOLS = {"get_context", "list_attempts", "read_file"}


def services_in(root: Path) -> Services:
    return build_services(
        content=content_root(),
        workspaces=root / "ws",
        database=root / "practice.db",
    )


def call(services: Services, tool: str, **arguments: str) -> CallToolResult:
    """One tool call over a fresh in-process session."""

    async def go() -> CallToolResult:
        async with Client(build_server(services)) as client:
            return await client.call_tool(tool, dict(arguments))

    return anyio.run(go)


def text_of(result: CallToolResult) -> str:
    """The single text block every tool here answers with."""
    (block,) = result.content
    assert isinstance(block, TextContent)
    return block.text


@dataclass(frozen=True)
class Shared:
    """Two open attempts over one set of services, for the read-only tests.

    The kata is marked as the one in front of the solver (ADR 0026) and stays
    so: nothing else in this file marks either of them.
    """

    services: Services
    scenario: AttemptId
    kata: AttemptId


@pytest.fixture(scope="module")
def shared(tmp_path_factory: pytest.TempPathFactory) -> Shared:
    """A scenario with one command run in it, and a kata, both left open."""
    services = services_in(tmp_path_factory.mktemp("mcp"))
    scenario = services.start_attempt(REVERT).attempt.id
    services.run_scenario_command(scenario, "git log --oneline")
    kata = services.start_attempt(TWO_SUM).attempt.id
    services.mark_current_attempt(kata)
    return Shared(services=services, scenario=scenario, kata=kata)


# --- what a client is told on connecting -----------------------------------


def test_the_server_introduces_itself_and_says_how_to_use_it(shared: Shared) -> None:
    async def go() -> tuple[str, str | None]:
        async with Client(build_server(shared.services)) as client:
            assert client.server_info is not None
            return client.server_info.name, client.instructions

    name, instructions = anyio.run(go)

    assert name == SERVER_NAME
    assert instructions == SERVER_INSTRUCTIONS
    assert "read-only" in SERVER_INSTRUCTIONS


def test_it_advertises_three_tools_and_every_one_is_marked_read_only(
    shared: Shared,
) -> None:
    """The annotation is the claim in the vocabulary a client can act on: one
    that asks before running a tool that writes has nothing to ask about here.
    A fourth tool added without it fails this by name.
    """

    async def go() -> dict[str, tuple[bool | None, bool | None]]:
        async with Client(build_server(shared.services)) as client:
            listed = await client.list_tools()
            return {
                tool.name: (
                    tool.annotations.read_only_hint if tool.annotations else None,
                    tool.annotations.destructive_hint if tool.annotations else None,
                )
                for tool in listed.tools
            }

    tools = anyio.run(go)

    assert set(tools) == TOOLS
    assert all(hints == (True, False) for hints in tools.values()), tools


def test_no_tool_takes_anything_that_could_be_a_command(shared: Shared) -> None:
    """The fourth tool that was not built. A parameter named for a command line
    appearing in a schema is the smallest sign that somebody built it.
    """

    async def go() -> set[str]:
        async with Client(build_server(shared.services)) as client:
            listed = await client.list_tools()
            return {
                name
                for tool in listed.tools
                for name in tool.input_schema.get("properties", {})
            }

    assert anyio.run(go) == {"attempt_id", "path", "rev"}


def ask(services: Services, question: str | None = None) -> str:
    """The `tutor` prompt, fetched the way a client's slash command fetches it:
    whatever was typed after the command arrives as the first argument.
    """

    async def go() -> str:
        async with Client(build_server(services)) as client:
            arguments = {} if question is None else {"question": question}
            got = await client.get_prompt("tutor", arguments)
            (message,) = got.messages
            assert isinstance(message.content, TextContent)
            return message.content.text

    return anyio.run(go)


def test_the_tutor_prompts_one_argument_is_the_question(shared: Shared) -> None:
    """Found by a person typing `/swe-practice:tutor hows the repo looking?`.

    A client passes the text after a slash command as the prompt's first
    argument. The first version's first argument was an attempt id, so that
    sentence was parsed as a uuid and the command died.
    """

    async def go() -> list[tuple[str, bool | None]]:
        async with Client(build_server(shared.services)) as client:
            listed = await client.list_prompts()
            (prompt,) = listed.prompts
            assert prompt.name == "tutor"
            return [(a.name, a.required) for a in prompt.arguments or []]

    assert anyio.run(go) == [("question", False)]


def test_the_tutor_prompt_is_the_context_with_the_question_under_it(
    tmp_path: Path,
) -> None:
    services = services_in(tmp_path)
    services.start_attempt(TWO_SUM)

    text = ask(services, "hows the repo looking?")

    assert text.startswith(TUTOR_PROMPT)
    assert "# Two Sum" in text
    assert text.endswith("## My question\n\nhows the repo looking?\n")


def test_the_tutor_prompt_needs_no_question(tmp_path: Path) -> None:
    services = services_in(tmp_path)
    services.start_attempt(TWO_SUM)

    text = ask(services)

    assert text.startswith(TUTOR_PROMPT)
    assert "## My question" not in text


def test_with_nothing_open_the_prompt_says_so_instead_of_failing(
    tmp_path: Path,
) -> None:
    """The other half of the same report: no attempt was open, and the reason
    reached the person as "Internal server error". A prompt has no failed-call
    result to carry a sentence, so the sentence is the prompt.
    """
    text = ask(services_in(tmp_path), "hows the repo looking?")

    assert "no attempt is open" in text
    assert "Do not guess" in text
    assert text.endswith("## My question\n\nhows the repo looking?\n")
    assert TUTOR_PROMPT not in text


def test_with_two_open_the_prompt_is_about_the_current_one(
    shared: Shared,
) -> None:
    """Found by a person, like the two above: an unfinished attempt left open
    made every `/swe-practice:tutor` an argument about which one was meant.
    """
    text = ask(shared.services, "what did I break?")

    assert text.startswith(TUTOR_PROMPT)
    assert "# Two Sum" in text
    assert "Undo a commit that is already on origin" not in text


def test_with_several_open_and_none_current_the_prompt_lists_them(
    tmp_path: Path,
) -> None:
    services, first, second = two_open_and_none_current(tmp_path)

    text = ask(services, "what did I break?")

    assert "2 attempts are open and none of them is marked as current" in text
    assert str(first) in text
    assert str(second) in text
    assert "call get_context with its id" in text


def test_an_open_interviews_prompt_says_why_instead_of_failing(
    tmp_path: Path,
) -> None:
    services = services_in(tmp_path)
    services.start_attempt(TWO_SUM, mode=AttemptMode.INTERVIEW)

    text = ask(services, "any hints?")

    assert "interview mode withholds the tutor" in text
    assert "# Two Sum" not in text


# --- get_context -----------------------------------------------------------


def test_get_context_is_the_attempt_read_from_the_real_repository(
    shared: Shared,
) -> None:
    result = call(shared.services, "get_context", attempt_id=str(shared.scenario))

    assert not result.is_error
    text = text_of(result)
    assert text.startswith(TUTOR_PROMPT)
    assert "**1.** Ran `git log --oneline` (exit 0)" in text
    assert "(HEAD, main, origin/main) Rename parse_line to parse" in text
    # The boundary is the use case's, and it holds through a fourth surface.
    assert "git revert" not in text
    assert "## The author's notes" not in text


def test_with_two_attempts_open_no_id_means_the_one_opened_last(
    shared: Shared,
) -> None:
    """Read, not guessed: the kata is the one marked (ADR 0026)."""
    result = call(shared.services, "get_context")

    assert not result.is_error
    text = text_of(result)
    assert "# Two Sum" in text
    assert "Undo a commit that is already on origin" not in text


def test_read_file_without_an_id_reads_the_attempt_get_context_described(
    shared: Shared,
) -> None:
    """One resolver for both, so a tutor that was shown the kata cannot then be
    handed a file out of the scenario's repository.
    """
    stub = call(shared.services, "read_file", path="stub.py")
    script = call(shared.services, "read_file", path="build.sh")

    assert not stub.is_error
    assert "def two_sum" in text_of(stub)
    assert script.is_error


def test_list_attempts_names_each_open_attempt_and_marks_the_current_one(
    shared: Shared,
) -> None:
    text = text_of(call(shared.services, "list_attempts"))

    assert f"{shared.scenario}  Undo a commit that is already on origin (1 " in text
    assert f"{shared.kata}  Two Sum (current, 0 commands run" in text


# --- read_file -------------------------------------------------------------


def test_read_file_reads_the_working_tree(shared: Shared) -> None:
    result = call(
        shared.services, "read_file", attempt_id=str(shared.scenario), path="build.sh"
    )

    assert not result.is_error
    assert "parse_line" in text_of(result)


def test_read_file_reads_a_committed_copy_at_a_revision(shared: Shared) -> None:
    """The bad commit renamed the function, so the two revisions differ in
    exactly the word the exercise is about.
    """
    services, attempt = shared.services, str(shared.scenario)

    now = text_of(call(services, "read_file", attempt_id=attempt, path="parser.py"))
    before = text_of(
        call(services, "read_file", attempt_id=attempt, path="parser.py", rev="HEAD~1")
    )

    assert "def parse(" in now
    assert "def parse_line(" in before


def test_a_file_that_is_not_there_is_a_failed_call_that_says_so(
    shared: Shared,
) -> None:
    result = call(
        shared.services, "read_file", attempt_id=str(shared.scenario), path="nope.py"
    )

    assert result.is_error
    assert "no readable file 'nope.py' in the working tree" in text_of(result)


def test_a_revision_that_is_really_an_option_never_reaches_git(
    shared: Shared,
) -> None:
    """Against real git, where it matters: `git show --output=FILE` opens FILE
    for writing. Refused by the use case, and nothing appears in the repository.
    """
    exercise = shared.services.content.get(REVERT)
    assert exercise is not None
    workspace = shared.services.provisioner.attach(exercise, shared.scenario)
    assert workspace is not None
    repo = workspace.resolve("build.sh").parent
    before = sorted(path.name for path in repo.iterdir())

    result = call(
        shared.services,
        "read_file",
        attempt_id=str(shared.scenario),
        path="build.sh",
        rev="--output=pwned.txt",
    )

    assert result.is_error
    assert "cannot begin with a hyphen" in text_of(result)
    assert sorted(path.name for path in repo.iterdir()) == before


def test_a_katas_hidden_suite_is_refused_and_its_own_file_is_not(
    shared: Shared,
) -> None:
    """The suite is really there -- this is a provisioned workspace -- so the
    refusal is the allowlist working and not a file that happened to be absent.
    """
    services, attempt = shared.services, str(shared.kata)

    suite = call(services, "read_file", attempt_id=attempt, path="tests.py")
    stub = call(services, "read_file", attempt_id=attempt, path="stub.py")

    assert suite.is_error
    assert "may read stub.py" in text_of(suite)
    assert not stub.is_error
    assert "def two_sum" in text_of(stub)


def test_a_malformed_attempt_id_is_a_sentence_not_a_crash(shared: Shared) -> None:
    result = call(shared.services, "get_context", attempt_id="oops")

    assert result.is_error
    assert "not a valid attempt id" in text_of(result)


# --- which attempt, when nobody says ---------------------------------------


def two_open_and_none_current(tmp_path: Path) -> tuple[Services, AttemptId, AttemptId]:
    """Two katas left open, and a third that was current until it was abandoned."""
    services = services_in(tmp_path)
    first = services.start_attempt(TWO_SUM).attempt.id
    second = services.start_attempt(STAIRS).attempt.id
    third = services.start_attempt(TWO_SUM).attempt.id
    services.mark_current_attempt(third)
    services.abandon_attempt(third)
    return services, first, second


def test_going_back_to_an_older_attempt_makes_it_the_one_a_tutor_is_shown(
    tmp_path: Path,
) -> None:
    """The case that rules out inferring it from the log. Nothing has been run
    or saved in the older attempt since the newer one was started -- editing a
    kata records nothing until it is submitted -- and it is the one on screen.
    """
    services = services_in(tmp_path)
    older = services.start_attempt(TWO_SUM).attempt.id
    newer = services.start_attempt(STAIRS).attempt.id
    services.mark_current_attempt(newer)
    assert "# Ways to Climb the Stairs" in text_of(call(services, "get_context"))

    services.mark_current_attempt(older)

    assert "# Two Sum" in text_of(call(services, "get_context"))


def test_with_several_open_and_none_current_it_asks_rather_than_guessing(
    tmp_path: Path,
) -> None:
    """What is left of ADR 0024's refusal, and the reason it is left: a tutor
    confidently describing the wrong repository is still the failure worth one.
    The refusal carries both ids and says how to avoid needing them.
    """
    services, first, second = two_open_and_none_current(tmp_path)

    result = call(services, "get_context")

    assert result.is_error
    text = text_of(result)
    assert "2 attempts are open and none of them is marked as current" in text
    assert "Bringing one to the front in the practice app marks it." in text
    assert str(first) in text
    assert str(second) in text
    assert "current," not in text_of(call(services, "list_attempts"))


def test_the_attempt_just_submitted_is_the_one_a_tutor_is_shown(
    tmp_path: Path,
) -> None:
    """**The review's first finding, over the real adapters.** One attempt left
    unfinished, another worked and submitted, and the question is what went
    wrong. The stale one is the only attempt still open, and the first version
    handed it over because of that.
    """
    services = services_in(tmp_path)
    stale = services.start_attempt(STAIRS).attempt.id
    worked = services.start_attempt(TWO_SUM).attempt.id
    services.mark_current_attempt(worked)
    services.submit_solution(worked, source="def two_sum(values, target): ...")

    text = text_of(call(services, "get_context"))
    listing = text_of(call(services, "list_attempts"))

    assert "# Two Sum" in text
    assert "## The verdict" in text
    assert "Ways to Climb the Stairs" not in text
    # The listing is of what is open, so it says where the current one went.
    assert f"{stale}  Ways to Climb the Stairs (0 commands run" in listing
    assert f"{worked}  finished, and the last one the user had in front" in listing


# --- the three states the shared attempt is not in -------------------------


def test_with_nothing_open_it_says_how_to_start(tmp_path: Path) -> None:
    services = services_in(tmp_path)

    context = call(services, "get_context")

    assert context.is_error
    assert "no attempt is open" in text_of(context)
    assert text_of(call(services, "list_attempts")) == "No attempt is open."


def test_with_one_attempt_open_no_id_is_needed(tmp_path: Path) -> None:
    services = services_in(tmp_path)
    services.start_attempt(TWO_SUM)

    result = call(services, "get_context")

    assert not result.is_error
    assert "# Two Sum" in text_of(result)


def test_an_open_interview_is_refused_by_every_tool_that_reads_it(
    tmp_path: Path,
) -> None:
    """Through the attempt's own policy, so a fourth surface did not have to be
    taught the rule -- and it is listed, marked, so a client can see why.
    """
    services = services_in(tmp_path)
    services.start_attempt(TWO_SUM, mode=AttemptMode.INTERVIEW)

    context = call(services, "get_context")
    file = call(services, "read_file", path="stub.py")

    assert context.is_error
    assert "interview mode withholds the tutor" in text_of(context)
    assert file.is_error
    assert "interview mode withholds the tutor" in text_of(file)
    assert "interview: no tutor until it is finished" in text_of(
        call(services, "list_attempts")
    )


def test_a_finished_attempt_is_a_post_mortem_by_id(tmp_path: Path) -> None:
    services = services_in(tmp_path)
    attempt = services.start_attempt(REVERT).attempt.id
    services.submit_scenario(attempt)

    result = call(services, "get_context", attempt_id=str(attempt))

    assert not result.is_error
    text = text_of(result)
    assert "## The verdict\n\nOutcome: fail" in text
    assert "## The author's notes" in text


# --- and none of it changed anything ---------------------------------------


def test_after_all_of_that_the_shared_attempts_are_exactly_as_they_were(
    shared: Shared,
) -> None:
    """Last in the file on purpose. Every test above called a tool against these
    two attempts; the log still holds the one command this module ran itself,
    and the repository is where the fixture left it.
    """
    scenario = shared.services.attempts.get(shared.scenario)
    kata = shared.services.attempts.get(shared.kata)
    assert scenario is not None
    assert kata is not None

    assert [run.command_line for run in scenario.commands] == ["git log --oneline"]
    assert len(scenario.events) == 1
    assert kata.events == ()

    view = shared.services.inspect_repository(shared.scenario)
    assert view is not None
    assert view.status.is_pristine
    assert view.head_branch == "main"
    assert (
        view.branches["refs/heads/main"]
        == (view.remote_branches["refs/remotes/origin/main"])
    )
