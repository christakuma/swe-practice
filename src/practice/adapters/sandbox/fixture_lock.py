"""`content/fixtures.lock` — the cross-platform determinism claim, as a file.

PLAN.md §11 sets the Phase 3 exit criterion as *the same fixture produces
byte-identical commit hashes on Windows and Linux CI*, and is specific about how
not to prove it: **not** by hard-coding a literal hash in a test. The difference
matters. A test asserting `c1 == "906e5c9"` fails identically whether someone
edited the fixture, someone broke the pinned environment, or git changed its
default object format — and all three produce the same red build with no
indication which happened.

A lock file separates them. Both CI jobs run every fixture and compare against
one committed record, so:

* a fixture edit shows up as a diff the author regenerates and reviews;
* a broken environment shows up as one platform disagreeing with the file while
  the other agrees;
* a git upgrade that changes hashing shows up as *everything* moving at once,
  which is a conversation rather than a mystery.

**It records refs as well as aliases.** The aliases are the commits, which is
what the criterion is about. The refs catch a class of fixture bug the commits
cannot: a fixture that builds the right history and leaves `origin/main` in the
wrong place still produces identical aliases, and `ref_unchanged` would then be
checking against a snapshot that was wrong from the start.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

import yaml

from practice.adapters.sandbox.provisioner import SubprocessSandboxProvisioner
from practice.domain.exercise import GitScenarioSpec
from practice.domain.ids import AttemptId

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.exercise import Exercise

__all__ = [
    "LOCK_FILENAME",
    "FixtureFingerprint",
    "compare",
    "fingerprint_library",
    "lock_path",
    "parse",
    "render",
]

LOCK_FILENAME: Final = "fixtures.lock"

_HEADER: Final = """\
# Fixture determinism, verified rather than asserted.
#
# Every git scenario's fixture is run and its commit aliases and refs recorded
# here. CI runs the same thing on Linux and on Windows and compares against
# this file, which is what makes "identical hashes on every platform" a checked
# claim instead of a hopeful one (docs/PLAN.md 6.1, 11).
#
# Regenerate with:  uv run practice fixtures --write
# Check with:       uv run practice fixtures --check
#
# A diff here is never noise. One exercise moving means its fixture changed.
# One platform disagreeing means the pinned environment broke. EVERYTHING
# moving at once means git changed how it hashes -- most likely a new default
# object format -- and that is a decision to make, not a build to fix.
"""


@dataclass(frozen=True, slots=True)
class FixtureFingerprint:
    """What one fixture deterministically produces.

    Hashes are held as plain strings rather than `Sha`, because this type's job
    is serialisation and a round trip through YAML should not be able to fail on
    a value the lock file already contains. `Sha` validated them on the way in,
    where a malformed hash is an actual bug.
    """

    exercise_id: str
    aliases: Mapping[str, str]
    refs: Mapping[str, str]

    def as_document(self) -> dict[str, dict[str, str]]:
        """The YAML shape: sorted, so a diff only ever shows a real change."""
        return {
            "aliases": dict(sorted(self.aliases.items())),
            "refs": dict(sorted(self.refs.items())),
        }


def lock_path(content_root: Path) -> Path:
    """Where the lock file lives: beside the tracks, inside the library."""
    return content_root / LOCK_FILENAME


def fingerprint_library(
    exercises: Sequence[Exercise],
    *,
    content_root: Path,
    workspace_root: Path | None = None,
) -> tuple[FixtureFingerprint, ...]:
    """Run every git scenario's fixture and record what it produced.

    Provisions into a temp directory rather than the real workspace root, so
    checking the lock file cannot collide with an attempt the developer has open
    — and so nothing it leaves behind is reported by `practice gc` as if it were
    an abandoned session.

    Katas are skipped rather than fingerprinted: they have no fixture and no
    repository, so there is nothing here that could differ between platforms.
    """
    scenarios = [
        exercise for exercise in exercises if isinstance(exercise.spec, GitScenarioSpec)
    ]
    if not scenarios:
        return ()

    if workspace_root is not None:
        return _fingerprint_into(scenarios, content_root, workspace_root)
    with tempfile.TemporaryDirectory(prefix="practice-fixtures-") as temporary:
        return _fingerprint_into(scenarios, content_root, Path(temporary))


def _fingerprint_into(
    scenarios: Sequence[Exercise], content_root: Path, workspace_root: Path
) -> tuple[FixtureFingerprint, ...]:
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root, workspace_root=workspace_root
    )
    fingerprints = []
    for index, exercise in enumerate(scenarios):
        # A distinct attempt id per exercise, so that a fixture which fails
        # leaves its workspace behind for inspection without the next one
        # colliding with it.
        workspace = provisioner.provision(exercise, _attempt_id(index))
        fingerprints.append(
            FixtureFingerprint(
                exercise_id=str(exercise.id),
                aliases={name: sha.value for name, sha in workspace.aliases().items()},
                refs={name: sha.value for name, sha in workspace.snapshot().items()},
            )
        )
        workspace.dispose()
    return tuple(sorted(fingerprints, key=lambda found: found.exercise_id))


def _attempt_id(index: int) -> AttemptId:
    """A fixed, readable attempt id. These workspaces are never resumed."""
    return AttemptId.parse(f"00000000-0000-4000-8000-{index:012d}")


def render(fingerprints: Sequence[FixtureFingerprint]) -> str:
    """The lock file's text, header and all."""
    body = {found.exercise_id: found.as_document() for found in fingerprints}
    return _HEADER + yaml.safe_dump(body, sort_keys=True, default_flow_style=False)


def parse(text: str) -> tuple[FixtureFingerprint, ...]:
    """Read a lock file. A malformed one is an empty one.

    Tolerant because the only caller compares the result against freshly
    computed fingerprints, and an unreadable lock file should be reported as
    *every exercise missing* — which names the problem and tells you to
    regenerate — rather than as a traceback from the YAML parser.
    """
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        return ()
    if not isinstance(document, dict):
        return ()

    found = []
    for exercise_id, entry in sorted(document.items()):
        if not isinstance(entry, dict):
            continue
        found.append(
            FixtureFingerprint(
                exercise_id=str(exercise_id),
                aliases=_string_map(entry.get("aliases")),
                refs=_string_map(entry.get("refs")),
            )
        )
    return tuple(found)


def _string_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def compare(
    expected: Sequence[FixtureFingerprint], actual: Sequence[FixtureFingerprint]
) -> tuple[str, ...]:
    """Every way the lock file and this machine disagree, located.

    One problem per differing entry rather than one per file, because the whole
    reason for the lock file is that *which* thing moved is the diagnosis. A
    report that says "fixtures.lock is out of date" throws that away.
    """
    by_id = {found.exercise_id: found for found in expected}
    problems = []

    for found in actual:
        recorded = by_id.pop(found.exercise_id, None)
        if recorded is None:
            problems.append(
                f"{found.exercise_id}: not in {LOCK_FILENAME}; it is a new "
                f"exercise, or the lock file was never regenerated"
            )
            continue
        problems.extend(
            f"{found.exercise_id}: {problem}"
            for problem in _differences(recorded, found)
        )

    problems.extend(
        f"{exercise_id}: in {LOCK_FILENAME} but no longer in the library"
        for exercise_id in sorted(by_id)
    )
    return tuple(problems)


def _differences(recorded: FixtureFingerprint, found: FixtureFingerprint) -> list[str]:
    problems = []
    for label, was, now in (
        ("alias", recorded.aliases, found.aliases),
        ("ref", recorded.refs, found.refs),
    ):
        for name in sorted(set(was) | set(now)):
            before, after = was.get(name), now.get(name)
            if before == after:
                continue
            if before is None:
                problems.append(f"{label} {name} is new ({_short(after)})")
            elif after is None:
                problems.append(f"{label} {name} has gone (was {_short(before)})")
            else:
                problems.append(
                    f"{label} {name} is {_short(after)}, locked as {_short(before)}"
                )
    return problems


def _short(sha: str | None) -> str:
    """Seven characters, the abbreviation git itself uses for display."""
    return (sha or "")[:7] or "(missing)"
