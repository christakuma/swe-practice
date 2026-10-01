"""Reading, writing and diffing `content/fixtures.lock`.

Unit tests: rendering, parsing and comparing are pure string and dictionary
work, and the half that runs actual fixtures is in the integration and content
suites. Splitting them that way is what makes it cheap to test the cases that
matter most — a hash that moved, an exercise that was added, a lock file someone
mangled — none of which are reachable by running real fixtures, because real
fixtures are deterministic.
"""

from __future__ import annotations

from practice.adapters.sandbox.fixture_lock import (
    LOCK_FILENAME,
    FixtureFingerprint,
    compare,
    parse,
    render,
)

A_SHA = "906e5c939db46ea7fd2ffbb47f8e922e8dc52fe9"
ANOTHER_SHA = "dc5258712f544cbfe22f227ca575dc73977fa586"


def a_fingerprint(
    exercise_id: str = "git/revert-a-pushed-commit",
    *,
    aliases: dict[str, str] | None = None,
    refs: dict[str, str] | None = None,
) -> FixtureFingerprint:
    return FixtureFingerprint(
        exercise_id=exercise_id,
        aliases=aliases if aliases is not None else {"c1": A_SHA},
        refs=refs if refs is not None else {"refs/heads/main": A_SHA},
    )


# --- the round trip --------------------------------------------------------


def test_it_round_trips() -> None:
    """The property that matters most: what is written can be read back.

    Without it, `--write` followed by `--check` would fail on a library nobody
    had touched, and the lock file would be noise rather than a signal.
    """
    found = (a_fingerprint("git/a"), a_fingerprint("git/b"))

    assert parse(render(found)) == found


def test_it_carries_an_explanation() -> None:
    """A diff in a generated file with no header invites someone to "fix" it by
    editing the hashes, which is the one response that is always wrong.
    """
    text = render((a_fingerprint(),))

    assert "practice fixtures --write" in text
    assert text.startswith("#")


def test_entries_are_sorted() -> None:
    """So a diff only ever shows a real change, never a reordering."""
    text = render(
        (
            a_fingerprint("git/b", aliases={"c2": ANOTHER_SHA, "c1": A_SHA}),
            a_fingerprint("git/a"),
        )
    )

    assert text.index("git/a") < text.index("git/b")
    assert text.index("c1") < text.index("c2")


# --- parsing the things people do to files ---------------------------------


def test_a_missing_file_parses_as_nothing() -> None:
    assert parse("") == ()


def test_a_mangled_file_parses_as_nothing() -> None:
    """Reported as every exercise missing — which names the problem and says to
    regenerate — rather than as a traceback out of the YAML parser.
    """
    assert parse("{{ not: yaml: at all") == ()


def test_a_file_that_is_not_a_mapping_parses_as_nothing() -> None:
    assert parse("- just\n- a list\n") == ()


def test_a_malformed_entry_is_skipped_rather_than_fatal() -> None:
    """One mangled entry should not hide the other twenty."""
    found = parse("git/a: not-a-mapping\ngit/b:\n  aliases:\n    c1: " + A_SHA + "\n")

    assert [entry.exercise_id for entry in found] == ["git/b"]


# --- comparing -------------------------------------------------------------


def test_identical_fingerprints_have_no_problems() -> None:
    locked = (a_fingerprint(),)

    assert compare(locked, locked) == ()


def test_a_changed_commit_is_located() -> None:
    """The failure the lock file exists for, and the message has to say which
    exercise and which commit — "fixtures.lock is out of date" throws away the
    entire diagnosis.
    """
    locked = (a_fingerprint(aliases={"c1": A_SHA}),)
    found = (a_fingerprint(aliases={"c1": ANOTHER_SHA}),)

    (problem,) = compare(locked, found)

    assert "git/revert-a-pushed-commit" in problem
    assert "alias c1" in problem
    assert ANOTHER_SHA[:7] in problem
    assert A_SHA[:7] in problem


def test_a_changed_ref_is_located() -> None:
    """Refs are recorded as well as commits because a fixture can build the
    right history and still leave `origin/main` in the wrong place — identical
    aliases, and `ref_unchanged` checking against a snapshot that was wrong from
    the start.
    """
    locked = (a_fingerprint(refs={"refs/heads/main": A_SHA}),)
    found = (a_fingerprint(refs={"refs/heads/main": ANOTHER_SHA}),)

    (problem,) = compare(locked, found)

    assert "ref refs/heads/main" in problem


def test_a_new_commit_is_reported() -> None:
    locked = (a_fingerprint(aliases={"c1": A_SHA}),)
    found = (a_fingerprint(aliases={"c1": A_SHA, "c2": ANOTHER_SHA}),)

    (problem,) = compare(locked, found)

    assert "alias c2 is new" in problem


def test_a_removed_commit_is_reported() -> None:
    locked = (a_fingerprint(aliases={"c1": A_SHA, "c2": ANOTHER_SHA}),)
    found = (a_fingerprint(aliases={"c1": A_SHA}),)

    (problem,) = compare(locked, found)

    assert "alias c2 has gone" in problem


def test_a_new_exercise_is_reported() -> None:
    """Either someone added an exercise, or someone forgot to regenerate. The
    message says both, because the fix differs.
    """
    (problem,) = compare((), (a_fingerprint(),))

    assert f"not in {LOCK_FILENAME}" in problem


def test_a_removed_exercise_is_reported() -> None:
    """A lock file that silently kept entries for deleted exercises would grow
    forever and stop being reviewable.
    """
    (problem,) = compare((a_fingerprint(),), ())

    assert "no longer in the library" in problem


def test_every_difference_is_reported_not_just_the_first() -> None:
    """One run should show the whole picture.

    If a git upgrade changes hashing, every exercise moves at once — and seeing
    that is what tells you it is a decision to make rather than a build to fix.
    """
    locked = (a_fingerprint("git/a"), a_fingerprint("git/b"))
    found = (
        a_fingerprint("git/a", aliases={"c1": ANOTHER_SHA}),
        a_fingerprint("git/b", aliases={"c1": ANOTHER_SHA}),
    )

    problems = compare(locked, found)

    assert len(problems) == 2
