"""Every git command a scenario teaches is one a person would type.

A scenario teaches commands in three places: the prompt, the hints and the
reference solution, which a solver reads after conceding. An audit of all three
found the references full of flags no one types at a terminal, and the hints
had copied them: `git log --oneline --decorate --all` five times, `git status
--short --branch` in every reference, `git revert --no-edit HEAD`, `git stash
show --stat stash@{0}`, and a `git rev-parse` to compare two hashes the line
above had already printed. **The worst of them were the sandbox's doing.**
Output goes through a pipe, so git left decoration off, and `GIT_EDITOR=false`
failed a plain `git commit` concluding a merge and `git rebase --continue`.
The references worked around the sandbox, the workaround spread to commands
that never needed it (`revert` opens no editor without a terminal), and the
hints passed it on as the lesson. The fix was to the sandbox
(`adapters/sandbox/provisioner.py`, `env.py`), so the plain command now works;
this file stops the workarounds coming back.

**What makes a form human is evidence, not a feeling.** The method has three
tiers, applied in order:

1. `NOISE`: a flag that restates the default, or that only the sandbox needed,
   plus one style rule: `git status` takes no flags, because the long form is
   the one that prints git's advice, and that advice is half of what these
   exercises teach. `status -sb` is a real habit; it is ruled out here as a
   teaching choice, not as noise. Each entry says which reason applies.
2. `PLUMBING`: commands git documents as being for scripts. A person types
   `git log`; a script types `git rev-parse`.
3. `FORMS`: every flagged form that is left has to be listed here, with where a
   person would have met it. Accepted evidence: **git prints it** in its own
   advice (people copy what the error tells them), or the **Pro Git book** or a
   **man page's examples** show it as the way to do the task. Each one was
   checked against the book or the git 2.46 docs when it was added. A form
   nobody can find evidence for is the signal; rewriting the hint is usually
   the answer, not adding the entry.

**The rejected alternative was matching the docs mechanically.** Grepping
git's HTML docs for each form found `git log --oneline --all` *nowhere*, while
it appears in every team's aliases. Man pages describe options; they are not a
record of usage, so a mechanical oracle rejects the commonest commands. The
list is a reviewed judgment, and this test makes every new form a judgment
someone has to make. That is the same check `test_drills.py` runs on
assertions, and `test_every_listed_form_is_still_taught` deletes the stale ones
the same way.

Flagless forms (`git status`, `git branch feature/x HEAD@{2}`) pass without an
entry: a bare subcommand is the human form by definition. Counter-examples are
not checked, because they model a mistake. `notes.md` is not checked either:
it discusses flags as well as teaching them, and a rule that cannot tell those
apart would only be noise of its own.
"""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING, Final

import pytest

from practice.adapters.content import load_exercise
from practice.domain.commands import parse_command_list
from practice.domain.exercise import GitScenarioSpec
from tests.content.test_library import (
    CONTENT_ROOT,
    GIT_SCENARIO_DIRECTORIES,
)

if TYPE_CHECKING:
    from pathlib import Path

#: A form is the subcommand and its set of flags. Values and paths do not
#: matter: `git reset --hard ORIG_HEAD` and `--hard origin/main` are one form.
Form = tuple[str, frozenset[str]]

#: Subcommands whose next word picks the operation, so it is part of the form.
_TWO_WORD = frozenset({"stash", "bisect"})

#: A short flag that takes its value attached: `-Sfoo` is the form `-S`.
_ATTACHED = re.compile(r"^-([SGm])\S+$")

#: (subcommand, flag) -> why no one types it.
NOISE: Final[dict[tuple[str, str], str]] = {
    ("log", "--decorate"): (
        "log.decorate=auto has decorated at a terminal since git 2.13 "
        "(git-log(1)), and the sandbox pins it on"
    ),
    ("status", "--short"): "style rule: the long form prints git's advice",
    ("status", "-s"): "style rule: the long form prints git's advice",
    ("status", "--branch"): "the long form's first line already names the branch",
    ("status", "-b"): "the long form's first line already names the branch",
    ("revert", "--no-edit"): "revert opens no editor without a terminal",
    ("cherry-pick", "--no-edit"): "cherry-pick does not open an editor by default",
    ("merge", "--no-edit"): "merge opens no editor without a terminal",
    ("stash show", "--stat"): "the diffstat is what stash show prints by default",
    ("reset", "--mixed"): "--mixed is reset's default mode",
    ("log", "--format"): "a format string is for scripts; --oneline is for people",
    ("log", "--pretty"): "a format string is for scripts; --oneline is for people",
}

#: Git's plumbing, which git-scm.com's own command list files under "low-level
#: commands". The fixtures use some of it; a solver is never taught it.
PLUMBING: Final = frozenset(
    {
        "rev-parse",
        "cat-file",
        "update-ref",
        "symbolic-ref",
        "for-each-ref",
        "ls-tree",
        "ls-files",
        "hash-object",
        "rev-list",
        "merge-base",
    }
)

#: More flags than this on one command reads as a script.
MAX_FLAGS: Final = 3


def _form(sub: str, *flags: str) -> Form:
    return sub, frozenset(flags)


#: Every flagged form a scenario may teach, and where a person meets it.
FORMS: Final[dict[Form, str]] = {
    _form("log", "--oneline"): "Pro Git 3.1, which passes --decorate as well",
    _form("log", "--oneline", "-1"): "git-log(1): -<number> limits the output",
    _form("log", "--oneline", "--all"): (
        "Pro Git 3.1's `--oneline --decorate --graph --all`, without the "
        "decoration a terminal now does itself"
    ),
    _form("log", "--oneline", "--graph", "--all"): (
        "Pro Git 3.1, without the --decorate a terminal now does itself"
    ),
    _form("log", "-S"): "Pro Git 2.3: `git log -S function_name`",
    _form("log", "--oneline", "-S"): "Pro Git 2.3's -S, one line per commit",
    _form("log", "--diff-filter"): "the git user manual: `git log --diff-filter=A`",
    _form("log", "--diff-filter", "--oneline"): (
        "the git user manual's --diff-filter, one line per commit"
    ),
    _form("show", "--stat"): (
        "Pro Git 2.3's `git log --stat`; git-show(1) takes log's diff options"
    ),
    _form("diff", "--stat"): "git-diff(1); the same diffstat git prints after a merge",
    _form("branch", "-a"): "git-branch(1): list remote-tracking branches too",
    _form("branch", "-vv"): "Pro Git 3.5: `git branch -vv`",
    _form("branch", "-D"): (
        "git prints it: `git branch -d` on an unmerged branch says to run "
        "`git branch -D` if you are sure"
    ),
    _form("checkout", "-b"): "Pro Git 3.2: `git checkout -b iss53`",
    _form("commit", "-m"): "Pro Git 3.1: `git commit -m 'Initial commit'`",
    _form("commit", "--amend"): "Pro Git 2.4: `git commit --amend`",
    _form("commit", "--amend", "-m"): "git-commit(1): --amend takes -m like any commit",
    _form("commit", "--amend", "--no-edit"): "git-commit(1), under --no-edit",
    _form(
        "pull", "--rebase"
    ): "git-push(1): integrate with `git pull --rebase`, then push",
    _form("push", "-u"): (
        "git prints `git push --set-upstream origin <branch>` for a branch "
        "with no upstream, and -u is its short form (git-push(1))"
    ),
    _form("push", "--force-with-lease"): "git-push(1)",
    _form("rebase", "--continue"): "git prints it when a rebase stops",
    _form("rebase", "--skip"): "git prints it when a rebase stops",
    _form("rebase", "--onto"): "git-rebase(1)'s examples",
    _form("reset", "--hard"): "git-reset(1)'s examples",
    _form("reset", "--soft"): "git-reset(1)'s examples",
    _form("restore", "--source"): "git-restore(1)'s synopsis",
    _form("revert", "-m"): "git-revert(1): reverting a merge needs -m",
    _form("rm", "--cached"): "git-rm(1), and the advice `git status` prints",
}


def form_of(argv: list[str] | tuple[str, ...]) -> Form | None:
    """The form of one git command, or `None` if it is not one."""
    if len(argv) < 2 or argv[0] != "git":
        return None
    sub, rest = argv[1], list(argv[2:])
    if sub in _TWO_WORD and rest and not rest[0].startswith("-"):
        sub = f"{sub} {rest.pop(0)}"
    flags = set()
    for arg in rest:
        if arg == "--":
            break
        if not arg.startswith("-"):
            continue
        if arg.startswith("--"):
            flags.add(arg.split("=", 1)[0])
        elif arg[1:].isdigit():
            flags.add("-1")
        elif match := _ATTACHED.match(arg):
            flags.add(f"-{match.group(1)}")
        else:
            flags.add(arg)
    return sub, frozenset(flags)


def taught(directory: Path) -> list[tuple[str, list[str]]]:
    """Every git command the scenario shows a solver, with where it was."""
    exercise = load_exercise(directory)
    spec = exercise.spec
    assert isinstance(spec, GitScenarioSpec)
    found: list[tuple[str, list[str]]] = []
    reference = (directory / spec.reference).read_text(encoding="utf-8")
    for line in parse_command_list(reference):
        found.append((f"{spec.reference}:{line.lineno}", list(line.argv)))
    places = [("prompt", exercise.prompt)] + [
        (f"hint {n}", hint.text) for n, hint in enumerate(exercise.hints, 1)
    ]
    for place, text in places:
        for span in re.findall(r"`(git [^`]+)`", text):
            found.append((place, shlex.split(" ".join(span.split()))))
    return found


def _identify(directory: Path) -> str:
    return directory.relative_to(CONTENT_ROOT).as_posix()


@pytest.fixture(params=GIT_SCENARIO_DIRECTORIES, ids=_identify)
def scenario_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


def _shown(argv: list[str]) -> str:
    return " ".join(argv)


def test_it_teaches_no_flag_that_restates_a_default(scenario_directory: Path) -> None:
    """Tier one: the flags the audit removed, kept out."""
    problems = []
    for place, argv in taught(scenario_directory):
        form = form_of(argv)
        if form is None:
            continue
        sub, flags = form
        for flag in sorted(flags):
            # `--amend --no-edit` is the one --no-edit people do type.
            if (sub, flag) == ("commit", "--no-edit") and "--amend" not in flags:
                problems.append(
                    f"{place}: `{_shown(argv)}` -- git commit uses the "
                    "prepared message by itself"
                )
            elif reason := NOISE.get((sub, flag)):
                problems.append(f"{place}: `{_shown(argv)}` -- {flag}: {reason}")
    assert not problems, "\n".join(problems)


def test_it_teaches_no_plumbing(scenario_directory: Path) -> None:
    """Tier two. If a lesson seems to need plumbing, a porcelain command does it."""
    problems = [
        f"{place}: `{_shown(argv)}`"
        for place, argv in taught(scenario_directory)
        if (form := form_of(argv)) is not None and form[0] in PLUMBING
    ]
    assert not problems, "\n".join(problems)


def test_every_flagged_form_is_one_with_evidence(scenario_directory: Path) -> None:
    """Tier three. A failure here is a question, not a missing line in FORMS.

    Find where a person would meet the form: git's own output, Pro Git, a
    man page's examples. If you cannot, rewrite the hint rather than adding
    the entry.
    """
    problems = []
    for place, argv in taught(scenario_directory):
        form = form_of(argv)
        if form is None or not form[1]:
            continue
        if len(form[1]) > MAX_FLAGS:
            problems.append(
                f"{place}: `{_shown(argv)}` has more than {MAX_FLAGS} flags"
            )
        elif form not in FORMS and form[0] not in PLUMBING:
            flags = " ".join(sorted(form[1]))
            problems.append(
                f"{place}: `git {form[0]} {flags}` has no evidence in FORMS"
            )
    assert not problems, "\n".join(problems)


def test_every_listed_form_is_still_taught() -> None:
    """A FORMS entry nothing teaches is a licence nobody is using. Delete it."""
    used = {
        form
        for directory in GIT_SCENARIO_DIRECTORIES
        for _, argv in taught(directory)
        if (form := form_of(argv)) is not None
    }
    assert set(FORMS) - used == set()


def test_no_listed_form_contains_a_noise_flag() -> None:
    """The tiers cannot disagree: evidence cannot license a restated default."""
    clashes = [form for form in FORMS for flag in form[1] if (form[0], flag) in NOISE]
    assert not clashes
