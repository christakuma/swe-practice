"""`open_in_browser` — the three ways `webbrowser` can answer, and one sentence.

A unit test and not an integration one, because the thing being tested is the
translation and not the browser: a test that actually opened a tab would be a
test that opened a tab on a developer's machine, every run, and proved nothing
`webbrowser`'s own suite does not.

`monkeypatch.setattr(webbrowser, "open", ...)` is the whole seam, which is the
property the module docstring claims — the lookup happens at call time, so one
substitution covers every caller and there is no port to inject.
"""

from __future__ import annotations

import webbrowser
from typing import Any

import pytest

from practice.adapters.sandbox import open_in_browser

URL = "http://127.0.0.1:8765"


class Opener:
    """Stands in for `webbrowser.open` with a fixed answer."""

    def __init__(self, answer: bool | BaseException) -> None:
        self._answer = answer
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, **kwargs: Any) -> bool:
        self.calls.append((url, kwargs))
        if isinstance(self._answer, BaseException):
            raise self._answer
        return self._answer


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> Opener:
    opener = Opener(answer=True)
    monkeypatch.setattr(webbrowser, "open", opener)
    return opener


def test_a_handler_that_opens_the_tab_is_not_reported(opened: Opener) -> None:
    assert open_in_browser(URL) is None
    assert opened.calls == [(URL, {"new": 2})]


def test_a_handler_that_declines_is_reported_as_a_sentence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`False` rather than an exception, which is the documented signal."""
    monkeypatch.setattr(webbrowser, "open", Opener(answer=False))

    refusal = open_in_browser(URL)

    assert refusal is not None
    assert URL in refusal


def test_no_registered_handler_is_reported_rather_than_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The headless case, and the one a return-value-only caller would crash on.

    A container, a bare server, WSL without `wslu`: `webbrowser` raises here
    instead of returning. Not opening a browser must not stop the server, so
    this has to arrive as the same sentence as a decline.
    """
    monkeypatch.setattr(
        webbrowser, "open", Opener(answer=webbrowser.Error("no browser"))
    )

    refusal = open_in_browser(URL)

    assert refusal is not None
    assert URL in refusal


def test_it_asks_for_a_new_tab(opened: Opener) -> None:
    """`new=2`, so the app does not replace whatever the solver was reading."""
    open_in_browser(URL)

    assert opened.calls[0][1]["new"] == 2
