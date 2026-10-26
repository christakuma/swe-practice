"""One editor engine, on every page that edits code (Phase 27, ADR 0034).

The exit criterion is *"no page loads two editor engines"*, and the way it
could come back is not a deliberate second library: it is the next editing
surface being written as a bare `<textarea>` because that is the shortest thing,
or a template copying the old `CodeMirror.fromTextArea` block from a page that
still had one. So the rule is held at the two places it can break -- what the
templates say, and what the rendered pages carry.

The behaviour of the component is `test_editor_script.py`'s; this file is about
which pages use it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId
from practice.interface.web.app import templates_root
from practice.interface.web.vendor import static_root

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")

#: The old engine's API and its stylesheet's selectors -- what a copied block
#: would carry. Comments may name it (the ADR does); code may not.
OLD_ENGINE = re.compile(r"CodeMirror\.|\.CodeMirror|codemirror[-.]")


def test_no_template_or_script_of_ours_drives_the_old_engine() -> None:
    offenders = [
        path.relative_to(templates_root().parent).as_posix()
        for path in [*templates_root().rglob("*.html"), *static_root().glob("*")]
        if path.is_file() and OLD_ENGINE.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []


def test_the_only_editing_textarea_is_the_components() -> None:
    """Every other textarea in a template is read-only text to copy.

    The tutor bundle's is `readonly` -- a prompt to select and paste -- and is
    the one exception, named so a second one has to be argued for.
    """
    editing = [
        path.name
        for path in templates_root().rglob("*.html")
        if re.search(r"<textarea(?![^>]*readonly)", path.read_text(encoding="utf-8"))
    ]

    assert editing == ["code-editor.html"]


def test_a_kata_page_carries_one_editor_and_loads_one_script(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert body.count("data-code-editor=") == 1
    assert body.count('src="/static/editor.js"') == 1
    assert "codemirror" not in body.lower()


def test_the_page_points_the_script_at_the_vendored_directory(
    client: TestClient,
) -> None:
    body = client.get("/browse").text

    assert 'data-monaco="/static/vendor/monaco/vs"' in body


def test_the_script_and_the_files_it_loads_are_served(client: TestClient) -> None:
    """The local-path failure the offline grep cannot see, for the new loader.

    `base.html` names only `editor.js`; the loader, the core and the worker are
    reached by a path *built in the script*, which `test_offline.py`'s
    layout check does not follow. So they are requested.
    """
    for path in (
        "editor.js",
        "vendor/monaco/vs/loader.js",
        "vendor/monaco/vs/editor/editor.main.js",
        "vendor/monaco/vs/editor/editor.main.css",
        "vendor/monaco/vs/base/worker/workerMain.js",
        "vendor/monaco/vs/base/browser/ui/codicons/codicon/codicon.ttf",
        "vendor/monaco/vs/basic-languages/python/python.js",
        "vendor/monaco/vs/basic-languages/sql/sql.js",
    ):
        response = client.get(f"/static/{path}")
        assert response.status_code == 200, path
