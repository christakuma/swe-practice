"""Every variant on disk, held to everything a standard kata is -- and one thing
more.

A variant is a whole exercise (ADR 0028), so the claims `test_katas.py` makes
about a kata are the claims to make here: the reference passes, the stub fails,
the suite holds more than one test, the complexity is compared rather than
graded, constraints are stated, and every example gives the output it shows.
**Those tests are imported rather than restated**, with the fixture that says
*which directories* overridden below, so the two files cannot drift into
holding a kata and its twist to different standards.

A second file rather than a longer parameter list in the first, and that is
about wall-clock rather than tidiness: `--dist loadfile` gives a file to one
worker, `test_katas.py` is already the suite's critical path, and every variant
costs three pytest subprocesses. Here they run beside the standard katas
instead of after them.

**And then a third file, for the same reason.** With one variant per kata this
file was as long as the one it sits beside. A second variant for seventy-nine
of the katas would have made it nearly twice that, and the gate's floor is its
longest file. So the variants are dealt out between `SHARDS` files --
alternately, in directory order -- and this one grades the first share.
`test_variants_second_shard.py` grades the other, from these same tests, and
holds the check that the shares add up to everything. Dealt alternately rather
than by anything meaningful, because nothing meaningful divides them evenly:
which variant came first is an accident of when it was written, and "the katas
in the first half of the alphabet" is no less arbitrary than every other one.
ADR 0028 names a marked tier as the fix for this file growing; that is still
the fix if the *total* becomes the problem, and it is not what was needed for
the longest file.

**The one thing more is `test_its_base_solution_does_not_pass_it`.** A twist
that the standard answer already satisfies is not a twist -- it is the same
exercise listed twice, and a solver who chose "surprise me" would be handed a
problem they could paste their last answer into. So each variant's hidden suite
is run against its *base's* reference, and that has to fail. It is ADR 0022's
rule pointed at the content rather than at a test: the claim "this version is
different" is executed against the thing it claims to differ from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.domain.exercise import KataSpec
from practice.domain.verdict import Outcome

# The fixtures are imported for pytest to find, and the tests to be collected
# here a second time over the directories below.
from tests.content.test_katas import (  # noqa: F401
    CONTENT_ROOT,
    Grade,
    _identify,
    _read,
    exercise,
    git,
    grade,
    spec,
    stub_verdict,
    test_it_shows_more_than_one_example,
    test_it_states_its_constraints,
    test_its_declared_complexity_is_compared_rather_than_graded,
    test_its_examples_give_the_output_they_show,
    test_its_hidden_suite_holds_more_than_one_test,
    test_its_reference_solution_passes_every_check,
    test_its_stub_fails,
)

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise


#: How many test files the variants are graded across. Changing it means adding
#: or removing a file like `test_variants_second_shard.py`, and that file's
#: last test fails until the two agree.
SHARDS = 2


def _variant_directories() -> list[Path]:
    """Every kata that is a variant, found as defensively as the katas are."""
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            loaded = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(loaded.spec, KataSpec) and loaded.is_variant:
            found.append(directory)
    return found


ALL_VARIANT_DIRECTORIES = _variant_directories()


def shard(index: int) -> list[Path]:
    """Every `SHARDS`-th variant directory, starting from the `index`-th.

    Slices of one sorted list, so the shards are disjoint and complete by
    construction for as long as every index below `SHARDS` has a file.
    """
    return ALL_VARIANT_DIRECTORIES[index::SHARDS]


VARIANT_DIRECTORIES = shard(0)


@pytest.fixture(params=VARIANT_DIRECTORIES, ids=_identify)
def kata_directory(request: pytest.FixtureRequest) -> Path:
    """The override: the imported tests ask for this by name and get a variant."""
    directory: Path = request.param
    return directory


def test_there_are_variants_to_grade() -> None:
    """Without this, every parametrized test in this file is vacuously true."""
    assert VARIANT_DIRECTORIES


def test_its_base_solution_does_not_pass_it(
    grade: Grade,  # noqa: F811
    exercise: Exercise,  # noqa: F811
) -> None:
    """The standard answer, submitted to the twist, must fail.

    Read from the base's own directory and graded by the variant's suite,
    through the same path a solver's submission takes. A base whose function
    has a different name fails at the import, which is a legitimate way to be
    a different problem; one with the same name has to fail on behaviour.
    """
    assert exercise.variant is not None
    base_directory = CONTENT_ROOT / exercise.variant.of.value
    base = load_exercise(base_directory)
    assert isinstance(base.spec, KataSpec)

    verdict = grade(_read(base_directory, base.spec.reference), None)

    assert verdict.outcome is Outcome.FAIL, (
        f"{exercise.variant.of}'s reference solution passes {exercise.id}: the "
        f"twist changes nothing a solver would have to change"
    )
