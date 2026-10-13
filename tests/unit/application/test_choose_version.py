"""`ChooseVersion`: a base exercise and a choice, resolved to the id to start.

Everything a variant costs the application layer is in this one use case (ADR
0028), so these tests are the whole of that layer's claim about variants: what
each kind of choice resolves to, that a draw is offered every version and
nothing else, and that a name which is not a variant *of this exercise* is
refused rather than started.
"""

from __future__ import annotations

import pytest

from practice.application.errors import ExerciseNotFoundError
from practice.application.use_cases import RANDOM, ChooseVersion
from practice.domain.exercise import Variant
from practice.domain.ids import ExerciseId
from tests.fakes import FakeContentRepository, FixedChooser, a_kata, a_scenario

BASE = ExerciseId("katas/two-sum")
SORTED = ExerciseId("variants/two-sum-sorted")
THREE = ExerciseId("variants/two-sum-three-ways")
OTHER = ExerciseId("git/revert-a-pushed-commit")
OTHERS_VARIANT = ExerciseId("variants/revert-twice")


def _variant(exercise_id: ExerciseId, of: ExerciseId = BASE) -> Variant:
    del exercise_id
    return Variant(of=of, twist="The list is sorted.")


def _library() -> FakeContentRepository:
    """A kata with two variants, and another exercise with a variant of its own.

    The second variant is here for the refusal test: it is a real exercise that
    `get` would happily return, which is exactly what makes starting it from
    the wrong base a mistake worth refusing.
    """
    return FakeContentRepository(
        [
            a_kata(),
            # Declared out of id order, so "sorted by id" is a claim and not
            # an accident of how the fake was filled.
            a_kata(exercise_id=THREE.value, variant=_variant(THREE)),
            a_kata(exercise_id=SORTED.value, variant=_variant(SORTED)),
            a_scenario(),
            a_kata(exercise_id=OTHERS_VARIANT.value, variant=_variant(OTHER, of=OTHER)),
        ]
    )


def _choose(chooser: FixedChooser | None = None) -> ChooseVersion:
    return ChooseVersion(
        content=_library(), chooser=chooser if chooser is not None else FixedChooser()
    )


# --- the standard version ---------------------------------------------------


@pytest.mark.parametrize("choice", [None, ""])
def test_no_choice_is_the_standard_version(choice: str | None) -> None:
    """`None` is a caller that never heard of variants; the empty string is a
    form whose select was left on its first option. Both mean the problem as
    written, which is what keeps every older caller meaning what it meant.
    """
    assert _choose()(BASE, choice) == BASE


def test_the_choice_is_optional() -> None:
    assert _choose()(BASE) == BASE


def test_no_choice_makes_no_draw() -> None:
    chooser = FixedChooser()

    _choose(chooser)(BASE)

    assert chooser.offered == []


# --- a named variant ---------------------------------------------------------


def test_a_variant_is_chosen_by_its_slug() -> None:
    """What a terminal types: `--variant two-sum-sorted`."""
    assert _choose()(BASE, "two-sum-sorted") == SORTED


def test_a_variant_is_chosen_by_its_whole_id() -> None:
    """What a form's `<option>` holds."""
    assert _choose()(BASE, "variants/two-sum-three-ways") == THREE


def test_naming_a_variant_makes_no_draw() -> None:
    chooser = FixedChooser()

    _choose(chooser)(BASE, "two-sum-sorted")

    assert chooser.offered == []


def test_a_name_that_is_no_variant_is_refused_with_the_ones_that_are() -> None:
    with pytest.raises(ExerciseNotFoundError) as refusal:
        _choose()(BASE, "two-sum-backwards")

    message = str(refusal.value)
    assert "katas/two-sum has no variant called 'two-sum-backwards'" in message
    assert "two-sum-sorted, two-sum-three-ways" in message


def test_a_variant_of_a_different_exercise_is_refused() -> None:
    """It exists, and `get` would return it -- which is why this is refused
    here rather than left to fail. Starting it from the wrong base is a typo
    landing on a different problem.
    """
    with pytest.raises(ExerciseNotFoundError, match="has no variant called"):
        _choose()(BASE, OTHERS_VARIANT.value)


def test_the_standard_exercise_is_not_a_variant_of_itself() -> None:
    with pytest.raises(ExerciseNotFoundError, match="has no variant called"):
        _choose()(BASE, BASE.value)


def test_an_exercise_with_no_variants_says_so() -> None:
    lonely = ChooseVersion(
        content=FakeContentRepository([a_kata()]), chooser=FixedChooser()
    )

    with pytest.raises(ExerciseNotFoundError, match="its variants are: none"):
        lonely(BASE, "two-sum-sorted")


# --- a draw -------------------------------------------------------------------


def test_a_draw_is_offered_the_standard_version_and_every_variant() -> None:
    """The standard version is in the draw and comes first; the variants
    follow in id order. Nothing else is a candidate -- not the other exercise,
    and not its variant.
    """
    chooser = FixedChooser()

    _choose(chooser)(BASE, RANDOM)

    assert chooser.offered == [(BASE, SORTED, THREE)]


def test_a_draw_starts_whichever_version_came_up() -> None:
    assert _choose(FixedChooser(index=-1))(BASE, RANDOM) == THREE
    assert _choose(FixedChooser(index=1))(BASE, RANDOM) == SORTED


def test_a_draw_can_land_on_the_standard_version() -> None:
    """Which is the point of including it: a draw that could never be the
    problem as written would tell a solver with one variant what was coming.
    """
    assert _choose(FixedChooser(index=0))(BASE, RANDOM) == BASE


def test_a_draw_over_an_exercise_with_no_variants_is_that_exercise() -> None:
    chooser = FixedChooser()
    lonely = ChooseVersion(content=FakeContentRepository([a_kata()]), chooser=chooser)

    assert lonely(BASE, RANDOM) == BASE
    assert chooser.offered == [(BASE,)]


# --- an exercise that is not there --------------------------------------------


@pytest.mark.parametrize("choice", [None, RANDOM, "two-sum-sorted"])
def test_an_exercise_the_library_does_not_have_is_refused(choice: str | None) -> None:
    """Before the choice is looked at, so the message is about the exercise
    and not about a variant of something that does not exist.
    """
    with pytest.raises(ExerciseNotFoundError, match="no exercise with id katas/nope"):
        _choose()(ExerciseId("katas/nope"), choice)
