"""A trial: the Run button's result, and the three ways an example can come out.

Small, because the type is small -- but `passed` is the one rule on it that a
page colours a row by, and *matched*, *raised* and *did not run* are three
different things a solver needs told apart (ADR 0029).
"""

from __future__ import annotations

from practice.domain.trial import ExampleResult, Trial


def test_an_example_passes_when_the_value_matches() -> None:
    assert ExampleResult(input="f()", expected="1", actual="1").passed


def test_an_example_fails_when_the_value_differs() -> None:
    """Compared as `repr` strings, so `1` and `True` are different answers."""
    assert not ExampleResult(input="f()", expected="1", actual="True").passed


def test_an_example_that_raised_has_not_passed() -> None:
    raised = ExampleResult(input="f()", expected="None", error="IndexError: boom")

    assert not raised.passed


def test_a_trial_counts_the_examples_that_matched() -> None:
    trial = Trial(
        examples=(
            ExampleResult(input="a", expected="1", actual="1"),
            ExampleResult(input="b", expected="2", actual="3"),
        )
    )

    assert trial.ran
    assert trial.passed == 1
    assert not trial.all_passed


def test_a_trial_where_every_example_matched_is_all_passed() -> None:
    trial = Trial(examples=(ExampleResult(input="a", expected="1", actual="1"),))

    assert trial.all_passed


def test_a_trial_with_a_problem_did_not_run_and_did_not_pass() -> None:
    """*Nothing ran* is not *everything failed*: a source that does not import
    has no logic error to look for."""
    trial = Trial(problem="your solution could not be imported: SyntaxError")

    assert not trial.ran
    assert not trial.all_passed
    assert trial.passed == 0
