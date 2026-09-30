"""Where things live on this machine.

Small on purpose. The only question Phase 2 has to answer is "which directory
holds the exercises?", and the answer has to survive three callers with
different ideas about the working directory: the CLI, the content test suite,
and CI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

__all__ = ["CONTENT_ROOT_ENV", "content_root", "project_root"]

#: Overrides the default content root. The test suite uses it to point the CLI
#: at a fixture library; a second content library is not otherwise a feature.
CONTENT_ROOT_ENV: Final = "PRACTICE_CONTENT_ROOT"

_CONTENT_DIRNAME: Final = "content"


def project_root() -> Path:
    """The repository root: `src/practice/config.py` is three levels down.

    Derived from `__file__` rather than from the working directory, so
    `practice validate` finds the library from wherever it is invoked.

    This assumes the package is installed from a source checkout, which `uv
    sync` does and which is the only way this tool is meant to be run — it is a
    local practice environment, not something to `pip install` from an index. A
    wheel installed into `site-packages` would land here with no `content/`
    beside it, which is why `content_root` can be overridden outright.
    """
    return Path(__file__).resolve().parents[2]


def content_root() -> Path:
    """The exercise library, honouring `PRACTICE_CONTENT_ROOT` if it is set."""
    override = os.environ.get(CONTENT_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return project_root() / _CONTENT_DIRNAME
