"""The scaffolding works: the package imports and the toolchain can see it.

Phase 1 replaces this with real domain tests. It exists now so that Phase 0's
exit criterion — a green `uv run pytest` in CI on both platforms — is a claim
about something rather than an empty run.
"""

from __future__ import annotations

import practice
import practice.application
import practice.domain


def test_package_exposes_a_version() -> None:
    assert practice.__version__ == "0.1.0"


def test_domain_and_application_packages_are_importable() -> None:
    assert practice.domain.__doc__
    assert practice.application.__doc__
