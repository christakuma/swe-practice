"""Identifier value objects: what they accept, and what they refuse."""

from __future__ import annotations

from uuid import UUID

import pytest

from practice.domain.errors import DomainError, InvalidValueError
from practice.domain.ids import AttemptId, ExerciseId, Sha, tag


class TestExerciseId:
    def test_splits_into_track_and_slug(self) -> None:
        exercise_id = ExerciseId("git/recover-a-lost-commit")

        assert exercise_id.track == "git"
        assert exercise_id.slug == "recover-a-lost-commit"
        assert str(exercise_id) == "git/recover-a-lost-commit"

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "two-sum",  # no track
            "katas/two-sum/extra",  # three segments; the id is the content path
            "Katas/two-sum",  # uppercase
            "katas/two_sum",  # underscores
            "katas/-two-sum",  # leading hyphen
            "katas/two-sum-",  # trailing hyphen
            "katas//two-sum",  # empty segment
            " katas/two-sum",
        ],
    )
    def test_rejects_anything_that_is_not_track_slash_slug(self, value: str) -> None:
        with pytest.raises(InvalidValueError):
            ExerciseId(value)

    def test_sorts_by_value(self) -> None:
        ids = [ExerciseId("katas/two-sum"), ExerciseId("git/revert-a-pushed-commit")]

        assert [str(one) for one in sorted(ids)] == [
            "git/revert-a-pushed-commit",
            "katas/two-sum",
        ]

    def test_is_hashable_so_it_can_key_a_registry(self) -> None:
        assert len({ExerciseId("katas/two-sum"), ExerciseId("katas/two-sum")}) == 1


class TestAttemptId:
    def test_round_trips_through_its_string_form(self) -> None:
        attempt_id = AttemptId(UUID("6f3a1c2e-0000-4000-8000-000000000001"))

        assert AttemptId.parse(str(attempt_id)) == attempt_id

    def test_short_form_is_eight_hex_characters_for_the_workspace_name(self) -> None:
        attempt_id = AttemptId(UUID("6f3a1c2e-0000-4000-8000-000000000001"))

        assert attempt_id.short == "6f3a1c2e"

    def test_parse_rejects_a_non_uuid(self) -> None:
        with pytest.raises(InvalidValueError):
            AttemptId.parse("not-a-uuid")


class TestSha:
    def test_normalises_case_so_two_spellings_compare_equal(self) -> None:
        upper = Sha("A" * 40)
        lower = Sha("a" * 40)

        assert upper == lower
        assert upper.value == "a" * 40

    def test_short_form_matches_gits_own_abbreviation_length(self) -> None:
        assert Sha("0123456789abcdef" + "0" * 24).short == "0123456"

    def test_formats_as_the_full_hash(self) -> None:
        assert str(Sha("a" * 40)) == "a" * 40

    def test_accepts_sha256_length_too(self) -> None:
        assert Sha("f" * 64).value == "f" * 64

    @pytest.mark.parametrize("value", ["", "abc", "g" * 40, "a" * 41, "a" * 39])
    def test_rejects_anything_that_is_not_an_object_hash(self, value: str) -> None:
        with pytest.raises(InvalidValueError):
            Sha(value)


class TestTag:
    def test_returns_the_string_unchanged(self) -> None:
        assert tag("two-pointers") == "two-pointers"

    @pytest.mark.parametrize("value", ["", "Two-Pointers", "two pointers", "two_"])
    def test_rejects_anything_that_is_not_kebab_case(self, value: str) -> None:
        with pytest.raises(InvalidValueError):
            tag(value)


def test_invalid_value_is_both_a_domain_error_and_a_value_error() -> None:
    """Pydantic converts a ValueError raised in a validator into a field error.

    That is the entire reason for the double base class, so it gets a test of its
    own rather than being an implementation detail someone later "tidies up".
    """
    with pytest.raises(ValueError, match="exercise id"):
        ExerciseId("nope")

    with pytest.raises(DomainError):
        ExerciseId("nope")
