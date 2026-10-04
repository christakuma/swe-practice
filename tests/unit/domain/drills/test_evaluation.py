"""How a value becomes the text an author's YAML is compared against.

`as_text` and `expected_rows` are the two places `domain/drills/` makes a
*policy* decision rather than an assertion, so they are tested directly as well
as through the ten assertions. The cases here are the ones no drill in the
library reaches and every drill depends on being right: a blob, a boolean, and
the three shapes of malformed `rows:` an author can write.

The coverage gate is why they are a file of their own rather than four more
cases in `test_rows.py`. The gate covers `domain/` and `application/` at 100%
statement *and* branch, and these four branches are the ones the eight shipped
drills happen not to exercise — which is exactly the kind of gap a gate exists
to name, since "no current content reaches it" is not the same as "it is
right".
"""

from __future__ import annotations

import pytest

from practice.domain.checks.evaluation import CheckSpecError, Params
from practice.domain.drills.evaluation import NULL, as_text, expected_rows, single_row


def params(**values: object) -> Params:
    return Params(assertion="result_matches", values=values)  # type: ignore[arg-type]


class TestAsText:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("alice", "alice"),
            (2, "2"),
            (0, "0"),
            (77.5, "77.5"),
            (10.0, "10"),
            (2.3333333333333335, "2.33333"),
            (None, NULL),
        ],
    )
    def test_the_values_a_drill_actually_meets(
        self, value: object, expected: str
    ) -> None:
        assert as_text(value) == expected  # type: ignore[arg-type]

    def test_a_blob_is_a_placeholder_rather_than_a_decode_attempt(self) -> None:
        """No drill in the library stores one, and guessing an encoding to put
        bytes in a verdict panel would be inventing content.
        """
        assert as_text(b"\x00\x01") == "<blob>"

    def test_a_boolean_reads_as_the_integer_sqlite_would_have_stored(self) -> None:
        """SQLite has no boolean type and never returns one, but a fake and an
        author's YAML both can — and `True` must not read as `True` where the
        column holds `1`.

        The `isinstance(value, bool)` test is before the `float` and `int` ones
        deliberately: `bool` is a subclass of `int`, so the order is the
        behaviour.
        """
        assert as_text(True) == "1"
        assert as_text(False) == "0"

    def test_a_float_that_is_whole_loses_its_point_zero(self) -> None:
        """Which is what makes `ROUND(SUM(total), 2)` comparable to a YAML `10`.

        `%g` formatting rather than rounding — `the-two-biggest-spenders` says
        why the precision is the solver's job.
        """
        assert as_text(10.0) == as_text(10)


class TestExpectedRows:
    def test_a_list_of_rows_is_normalised_cell_by_cell(self) -> None:
        assert expected_rows(params(rows=(("alice", 2), ("bob", None)))) == (
            ("alice", "2"),
            ("bob", NULL),
        )

    def test_a_flat_row_is_accepted_as_a_list_of_one(self) -> None:
        assert expected_rows(params(rows=("alice", 2))) == (("alice", "2"),)

    @pytest.mark.parametrize("bad", ["alice", 2, True, ()])
    def test_a_rows_value_that_is_not_a_list_of_rows_is_refused(
        self, bad: object
    ) -> None:
        """A bare scalar and an empty list are both authoring mistakes, and both
        produce a check that can never pass — which is the vacuous-check failure
        §5.4 is about, pointing the other way.
        """
        with pytest.raises(CheckSpecError, match="non-empty list of rows"):
            expected_rows(params(rows=bad))

    @pytest.mark.parametrize("bad", [(("alice", 2), "bob"), (("alice", 2), ())])
    def test_a_row_that_is_not_a_list_of_values_is_refused(self, bad: object) -> None:
        """One well-formed row and one that is not. Mixed shapes are the version
        of this an author is most likely to write, because the first row looks
        right.
        """
        with pytest.raises(CheckSpecError, match="non-empty list of values"):
            expected_rows(params(rows=bad))

    def test_ragged_rows_are_refused(self) -> None:
        with pytest.raises(CheckSpecError, match="same number of values"):
            expected_rows(params(rows=(("alice", 2), ("bob",))))

    def test_a_nested_list_where_a_value_belongs_is_refused(self) -> None:
        with pytest.raises(CheckSpecError, match="nested list"):
            expected_rows(params(rows=((("alice", 2),),)))

    def test_a_missing_parameter_names_itself(self) -> None:
        with pytest.raises(CheckSpecError, match="missing required parameter 'rows'"):
            expected_rows(params())


class TestSingleRow:
    def test_one_row_comes_back_as_a_row(self) -> None:
        assert single_row(params(row=("alice", 2)), "row") == ("alice", "2")

    def test_more_than_one_row_is_refused_rather_than_truncated(self) -> None:
        """Grading the first silently would be a check that tests less than it
        says, which is the one failure mode a counter-example cannot catch.
        """
        with pytest.raises(CheckSpecError, match="takes one row, got 2"):
            single_row(params(row=(("alice", 2), ("bob", 0))), "row")
