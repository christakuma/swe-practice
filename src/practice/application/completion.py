"""Tab completion for the console: which word is being completed, and with what.

**Pure, and in the application layer rather than the browser.** The browser
could have been sent the refs and paths and left to complete them itself, which
is a request fewer per Tab. It would also have put the only interesting logic in
this feature, which word is the cursor in and what belongs in that position, in
the one place the coverage gate cannot see. So the browser sends the line and
applies the answer; this decides it, as a function of the line and a
`Vocabulary`, and is tested without a repository, a process or a page.

**It completes the way bash with git's completion script does, minus the
parts that would teach a flag.** The first word completes to a program the
exercise allows, the second word after `git` to a subcommand, then a remote
for `push`, `pull` and `fetch`, branches and tags for the commands that take a
revision, and paths for the ones that take a file. `rev:path` completes the
path after the colon, as in `git show main~3:tools/he<Tab>`. Flags are not
completed, deliberately: a list of a subcommand's flags is the vocabulary
`tests/content/test_git_commands_people_type.py` exists to keep out of the
hints, and a Tab key that offered `--decorate` would be the same mistake from
a different direction.

**Directories complete one level at a time**, `to` to `tools/` with no space
after, because that is what a shell does and because a list of every path under
a directory is a wall where a single step is an answer.

**Quoted words are not completed.** `write notes.md 'some text` is mid-string,
and a completion there would be guessing at a shell grammar this console does
not have (PLAN.md §8.1: there is no shell).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = ["Completion", "Vocabulary", "complete"]

#: Porcelain, as `git help` lists it for everyday use. Plumbing is left out for
#: the reason flags are: a Tab key teaches whatever it offers.
GIT_SUBCOMMANDS: Final = (
    "add",
    "bisect",
    "blame",
    "branch",
    "checkout",
    "cherry-pick",
    "clean",
    "commit",
    "diff",
    "fetch",
    "grep",
    "log",
    "merge",
    "mv",
    "pull",
    "push",
    "rebase",
    "reflog",
    "remote",
    "reset",
    "restore",
    "revert",
    "rm",
    "show",
    "stash",
    "status",
    "switch",
    "tag",
)

#: The second word after these picks an operation, like a subcommand of its own.
OPERATIONS: Final = {
    "stash": ("apply", "drop", "list", "pop", "push", "show"),
    "bisect": ("bad", "good", "log", "reset", "skip", "start"),
}

#: Subcommands whose arguments are files rather than revisions.
TAKES_PATHS: Final = frozenset({"add", "blame", "mv", "restore", "rm"})

#: Subcommands whose first argument is a remote: `git push origin main`.
TAKES_REMOTE: Final = frozenset({"fetch", "pull", "push"})


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """Everything a word could complete to, read from one attempt."""

    programs: frozenset[str]
    revisions: frozenset[str]
    paths: frozenset[str]
    remotes: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Completion:
    """What a Tab press should do to the line.

    `line` is the line with the word extended as far as every match agrees,
    plus a space when the match was unique and finished. `matches` is every
    candidate, sorted, so a second press with no progress can list them.
    """

    line: str
    matches: tuple[str, ...]


def complete(line: str, vocabulary: Vocabulary) -> Completion:
    """Complete the last word of `line`."""
    if line.count("'") % 2 or line.count('"') % 2:
        return Completion(line=line, matches=())

    words = line.split()
    # A line ending in a space is starting a new word, which is empty.
    word = words.pop() if line[-1:].strip() else ""
    head = line[: len(line) - len(word)]

    prefix, stem, candidates = _candidates(words, word, vocabulary)
    matches = tuple(sorted(c for c in candidates if c.startswith(stem)))
    if not matches:
        return Completion(line=line, matches=())

    common = _common_prefix(matches)
    finished = len(matches) == 1 and not common.endswith("/")
    return Completion(
        line=head + prefix + common + (" " if finished else ""),
        matches=matches,
    )


def _candidates(
    words: list[str], word: str, vocabulary: Vocabulary
) -> tuple[str, str, set[str]]:
    """The fixed prefix of the word, the part being completed, and the options."""
    if not words:
        return "", word, set(vocabulary.programs)
    if words[0] != "git":
        return "", word, _path_steps(vocabulary.paths, word)
    if ":" in word:
        revision, _, path = word.partition(":")
        return revision + ":", path, _path_steps(vocabulary.paths, path)
    return "", word, _git_argument(words[1:], word, vocabulary)


def _git_argument(after: list[str], word: str, vocabulary: Vocabulary) -> set[str]:
    """What a word after `git` can be, given the words between them."""
    if not after:
        return set(GIT_SUBCOMMANDS)
    subcommand = after[0]
    if after == [subcommand] and subcommand in OPERATIONS:
        return set(OPERATIONS[subcommand])
    if after == [subcommand] and subcommand in TAKES_REMOTE:
        return set(vocabulary.remotes)
    if word.startswith("-"):
        return set()
    if "--" in after or subcommand in TAKES_PATHS:
        return _path_steps(vocabulary.paths, word)
    return set(vocabulary.revisions)


def _path_steps(paths: frozenset[str], word: str) -> set[str]:
    """Each path cut off after the first directory past what is typed."""
    steps = set()
    for path in paths:
        if not path.startswith(word):
            continue
        slash = path.find("/", len(word))
        steps.add(path if slash == -1 else path[: slash + 1])
    return steps


def _common_prefix(words: tuple[str, ...]) -> str:
    first, last = min(words), max(words)
    length = 0
    while length < len(first) and first[length] == last[length]:
        length += 1
    return first[:length]
