"""Where things live on this machine.

Small on purpose. Three questions: which directory holds the exercises, where do
attempt workspaces go, and where is the database. All three answers have to
survive callers with different ideas about the working directory — the CLI, the
content test suite, and CI — and all three are overridable by an environment
variable, because every test that touches one needs to point somewhere
disposable.

**The database is the one piece of state here that is not disposable**, which is
why it goes in the *data* directory and the workspaces go in the *cache* one.
Clearing a cache is something a user or an operating system is entitled to do at
any time; losing every attempt you have ever made is not an acceptable outcome of
it. A workspace is rebuildable from a fixture, and `practice.db` is not
rebuildable from anything.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import platformdirs

__all__ = [
    "CONTENT_ROOT_ENV",
    "DATABASE_PATH_ENV",
    "WORKSPACE_ROOT_ENV",
    "cache_root",
    "content_root",
    "data_root",
    "database_path",
    "project_root",
    "workspace_root",
]

#: Overrides the default content root. The test suite uses it to point the CLI
#: at a fixture library; a second content library is not otherwise a feature.
CONTENT_ROOT_ENV: Final = "PRACTICE_CONTENT_ROOT"

#: Overrides where attempt workspaces are provisioned. Every sandbox test sets
#: it: a suite that provisioned into the real cache would collide with a session
#: the developer has open, and `practice gc` would then report test leftovers as
#: if they were real attempts.
WORKSPACE_ROOT_ENV: Final = "PRACTICE_WORKSPACE_ROOT"

#: Overrides where the database lives. Set by the test suite for every test
#: without exception: a suite that wrote to the real database would mix test
#: attempts into a real history, and `practice attempts` would then list them.
DATABASE_PATH_ENV: Final = "PRACTICE_DATABASE_PATH"

_CONTENT_DIRNAME: Final = "content"

#: The application name platformdirs keys the cache directory on. `appauthor`
#: is suppressed because on Windows the default nests `<author>/<name>`, and
#: every character of that path is a character `MAX_PATH` does not have to
#: spare (PLAN.md §8.1).
_APP_NAME: Final = "swe-practice"

#: The database file. One file, not a directory: SQLite's WAL and shared-memory
#: siblings sit next to it, and nothing else is stored.
_DATABASE_FILENAME: Final = "practice.db"

#: Workspaces live one level down rather than directly in the cache, so that
#: `practice gc` can enumerate a directory it is certain holds nothing else —
#: and so a future cache of anything else has somewhere to go that gc will not
#: mistake for an abandoned attempt.
_WORKSPACE_DIRNAME: Final = "ws"


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


def cache_root() -> Path:
    """The per-user cache directory. Not created here; the caller decides."""
    return Path(platformdirs.user_cache_dir(_APP_NAME, appauthor=False))


def workspace_root() -> Path:
    """Where attempt workspaces are provisioned.

    The user cache rather than the system temp directory, deliberately: a failed
    attempt has to survive for inspection, and some platforms sweep the temp
    directory out from under a running process (PLAN.md §8.1).
    """
    override = os.environ.get(WORKSPACE_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return cache_root() / _WORKSPACE_DIRNAME


def data_root() -> Path:
    """The per-user data directory. Not created here; the caller decides.

    Distinct from `cache_root` on purpose, and on every platform that
    distinguishes them: what is in here cannot be regenerated.
    """
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False))


def database_path() -> Path:
    """The SQLite file holding attempts and review cards.

    Honours `PRACTICE_DATABASE_PATH`, and the override is a *file* path rather
    than a directory, so a test can point two processes at one database without
    agreeing on a filename as well.
    """
    override = os.environ.get(DATABASE_PATH_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return data_root() / _DATABASE_FILENAME
