"""`/progress` and the two charts it is made of.

Split the way `test_commit_graph.py` splits: the renderers are driven directly
with summaries built to say one thing each, and the page is driven over HTTP to
prove it reaches them. Assertions on the SVG are about the properties a chart has
to have rather than about exact coordinates — a test pinning `x="13.33"` fails on
every layout change and catches none of the ones that matter.

The three properties worth pinning, because each of them is a decision the
module docstring argues for and a refactor could quietly drop: colours are CSS
variables rather than literals, every value is escaped, and every number is
readable without the picture.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, cast

from practice.application.progress import (
    DayActivity,
    Progress,
    TagMastery,
    summarise,
)
from practice.domain.ids import ExerciseId, tag
from practice.interface.web.charts import render_activity, render_mastery
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.domain.ids import Tag
    from tests.web.conftest import Wiring

TODAY = date(2026, 10, 2)
KATA = ExerciseId("katas/two-sum")
SOLUTION = "def two_sum(values, target):\n    return (0, 1)\n"


def a_progress(
    *,
    days: tuple[DayActivity, ...] = (),
    tags: tuple[TagMastery, ...] = (),
) -> Progress:
    """A summary assembled directly, so each chart test says one thing."""
    return Progress(
        attempts=(),
        passed=0,
        tags=tags,
        days=days,
        streak_days=0,
        scheduled=0,
    )


def a_window(*counts: tuple[int, int]) -> tuple[DayActivity, ...]:
    """`(attempts, passed)` per day, oldest first — the order a chart reads."""
    start = TODAY - timedelta(days=len(counts) - 1)
    return tuple(
        DayActivity(day=start + timedelta(days=offset), attempts=done, passed=won)
        for offset, (done, won) in enumerate(counts)
    )


# --- the activity chart ----------------------------------------------------


class TestTheActivityChart:
    def test_it_draws_a_bar_for_every_day_including_the_idle_ones(self) -> None:
        """The gaps are the information. A chart drawn only from the busy days
        makes a scattered month and a solid week look identical.
        """
        svg = render_activity(a_progress(days=a_window((2, 2), (0, 0), (1, 0))))

        assert svg.count("<rect") == 4  # three totals, one of them with a pass
        assert svg.count("<title>") == 3

    def test_each_bar_says_its_own_numbers(self) -> None:
        """A chart is the worst way to learn a number, so every bar carries one."""
        svg = render_activity(a_progress(days=a_window((2, 1))))

        assert "2026-10-02: 2 attempts, 1 passed" in svg

    def test_one_attempt_is_not_pluralised(self) -> None:
        svg = render_activity(a_progress(days=a_window((1, 0))))

        assert "1 attempt," in svg

    def test_the_passes_are_drawn_over_the_total_from_the_same_baseline(self) -> None:
        """Not a stack: a stack puts failures above passes and makes the failing
        days the tall ones, which is the opposite of the reading. Height is
        effort, colour is how it went.
        """
        svg = render_activity(a_progress(days=a_window((4, 1))))

        assert 'fill="var(--ink-dim)"' in svg
        assert 'fill="var(--pass)"' in svg
        # Both rectangles end at the baseline, so the pass bar is the shorter one
        # and starts lower down the drawing.
        assert svg.index('fill="var(--ink-dim)"') < svg.index('fill="var(--pass)"')

    def test_an_entirely_idle_window_does_not_divide_by_zero(self) -> None:
        """The one arithmetic error a chart can make silently: every bar would
        come out the same wrong height rather than raising.
        """
        svg = render_activity(a_progress(days=a_window((0, 0), (0, 0))))

        assert "<svg" in svg
        assert "0 attempts" in svg

    def test_it_labels_the_ends_of_the_window(self) -> None:
        svg = render_activity(a_progress(days=a_window((0, 0), (0, 0), (1, 1))))

        assert ">09-30<" in svg
        assert ">10-02<" in svg

    def test_it_says_what_it_is_for_a_reader_who_cannot_see_it(self) -> None:
        svg = render_activity(a_progress(days=a_window((3, 3), (1, 0))))

        assert 'role="img"' in svg
        assert "Activity over 2 days: 4 attempts, busiest day 3" in svg

    def test_a_summary_with_no_window_says_so_rather_than_drawing_nothing(
        self,
    ) -> None:
        assert "No window to draw" in render_activity(a_progress())

    def test_every_colour_is_a_custom_property(self) -> None:
        """A chart with `#83c98a` in it is the one element on the page that stops
        following the theme, and nothing would notice until someone looked.
        """
        svg = render_activity(a_progress(days=a_window((1, 1))))

        assert "#" not in svg


# --- the mastery chart -----------------------------------------------------


def a_tag(name: str, *, attempted: int, passed: int, lapses: int = 0) -> TagMastery:
    return TagMastery(tag=tag(name), attempted=attempted, passed=passed, lapses=lapses)


class TestTheMasteryChart:
    def test_one_row_per_tag_with_its_count_beside_it(self) -> None:
        svg = render_mastery(
            (
                a_tag("history", attempted=3, passed=1),
                a_tag("arrays", attempted=2, passed=2),
            )
        )

        assert svg.count("<g>") == 2
        assert ">1/3<" in svg
        assert ">2/2<" in svg

    def test_a_weak_tag_is_drawn_in_the_warning_colour(self) -> None:
        """`is_weak` is the one answer the chart and the dashboard's weakest
        list both read, so they cannot point at different rows.
        """
        svg = render_mastery((a_tag("history", attempted=2, passed=1),))

        assert 'fill="var(--note)"' in svg

    def test_a_tag_nothing_has_gone_wrong_with_is_not(self) -> None:
        svg = render_mastery((a_tag("arrays", attempted=2, passed=2),))

        assert 'fill="var(--pass)"' in svg
        assert 'fill="var(--note)"' not in svg

    def test_a_perfect_rate_with_lapses_behind_it_still_reads_as_weak(self) -> None:
        svg = render_mastery((a_tag("arrays", attempted=2, passed=2, lapses=1),))

        assert 'fill="var(--note)"' in svg
        assert "1 lapse</title>" in svg

    def test_each_row_says_its_own_numbers(self) -> None:
        svg = render_mastery((a_tag("history", attempted=3, passed=1, lapses=2),))

        assert "history: 1 of 3 passed, 2 lapses" in svg

    def test_a_long_tag_is_cut_rather_than_overrunning_the_bars(self) -> None:
        """Comparing lengths is the only thing this chart is for, so the longest
        tag must not shift every other row's bar out of alignment.
        """
        svg = render_mastery(
            (a_tag("a-very-long-tag-name-indeed", attempted=1, passed=1),)
        )

        assert "…" in svg
        assert "a-very-long-tag-name-indeed" in svg  # still in the `title`

    def test_no_tags_says_so_rather_than_drawing_an_empty_box(self) -> None:
        assert "no mastery to show" in render_mastery(())

    def test_every_colour_is_a_custom_property(self) -> None:
        svg = render_mastery((a_tag("arrays", attempted=1, passed=1),))

        assert "#" not in svg


def test_a_tag_whose_name_is_markup_is_escaped() -> None:
    """Tag names come out of exercise files, which are data. The rule is applied
    where the markup is built so that nobody has to re-derive which values are
    safe when a label starts coming from somewhere else.

    The cast is the test: `tag()` would refuse this string, and the renderer is
    held to escaping it anyway. A chart that trusted the validator two layers up
    would be one validator away from an injection.
    """
    hostile = cast("Tag", "<script>")

    svg = render_mastery((TagMastery(tag=hostile, attempted=1, passed=0, lapses=0),))

    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


# --- the page --------------------------------------------------------------


def solve(client: TestClient, wiring: Wiring, exercise_id: ExerciseId = KATA) -> None:
    started = wiring.services.start_attempt(exercise_id)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})


def test_the_page_renders_before_anything_is_graded(client: TestClient) -> None:
    """The state a fresh install is in, and the one a chart library would draw
    an empty axis for.
    """
    response = client.get("/progress")

    assert response.status_code == 200
    assert "0 graded attempts" in response.text
    assert "Nothing graded yet" in response.text
    assert "no mastery to show" in response.text


def test_it_reaches_both_charts(client: TestClient, wiring: Wiring) -> None:
    solve(client, wiring)

    body = client.get("/progress").text

    assert 'class="chart activity"' in body
    assert 'class="chart mastery"' in body


def test_it_prints_every_figure_in_words_as_well(
    client: TestClient, wiring: Wiring
) -> None:
    """A page whose content exists only inside an `svg` is one a printout, a
    screen reader and a copy-paste all lose.
    """
    solve(client, wiring)

    body = client.get("/progress").text

    assert "1 graded attempt, 1 passed (100%)" in body
    assert "Current streak <strong>1 day</strong>" in body
    assert "<td>arrays</td>" not in body  # the tag is a chip, not bare text
    assert "arrays" in body


def test_the_history_names_the_exercise_and_links_to_the_attempt(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})

    body = client.get("/progress").text

    assert f'href="/attempt/{started.attempt.id}"' in body
    assert "Two Sum" in body
    assert 'class="outcome-chip pass"' in body


def test_an_attempt_still_running_is_not_in_the_history(
    client: TestClient, wiring: Wiring
) -> None:
    wiring.services.start_attempt(KATA)

    assert "Nothing graded yet" in client.get("/progress").text


def test_an_attempt_whose_exercise_is_gone_is_listed_under_its_id(
    client: TestClient, wiring: Wiring
) -> None:
    """It happened. Hiding it would let a deleted exercise quietly rewrite the
    totals printed above it.
    """
    solve(client, wiring)
    wiring.content.forget(KATA)

    body = client.get("/progress").text

    assert "1 graded attempt" in body
    assert "katas/two-sum" in body


def test_the_page_is_linked_from_every_other_one(client: TestClient) -> None:
    assert '<a href="/progress">Progress</a>' in client.get("/browse").text


def test_the_summary_is_the_same_one_the_dashboard_reads() -> None:
    """Asserted through the pure function rather than by comparing two pages:
    one summary serves both, and the thing worth pinning is that the streak on
    `/progress` is computed from the same call the dashboard makes.
    """
    wiring = a_wiring()
    with client_for(wiring) as client:
        solve(client, wiring)
        dashboard = client.get("/").text
        progress = client.get("/progress").text

    kata = wiring.content.get(KATA)
    assert kata is not None
    expected = summarise(
        attempts=wiring.attempts.completed(),
        exercises={KATA: kata},
        cards=wiring.reviews.cards(),
        today=wiring.clock.today(),
    )
    assert f"<strong>{expected.streak_days} day</strong>" in dashboard
    assert f"<strong>{expected.streak_days} day</strong>" in progress
