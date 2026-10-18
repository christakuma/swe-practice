"""A container definition in memory, for the eleven assertions to be tested against.

The second implementation of `BuildQuery` (PLAN.md §13). **Built from answers,
not from a Dockerfile**: a test states *PID 1 is `/bin/sh`* or *`.env` reaches
the image* directly, which is all an assertion reads. A fake that parsed
Dockerfiles would be a second, worse parser and prove nothing the real one
does not.

So it can say things the real adapter cannot, such as a process with no stages or
an error alongside a user. That is `FakeDrillQuery`'s property and for its
reason: what an assertion does with an unreachable state is what a broken
exercise exercises. `tests/integration/container/test_conformance.py` holds
the two to the same answers on the states that are reachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ports import Account, Instruction, PathAccess, PathEntry, Stage

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__ = [
    "ROOT",
    "FakeBuildQuery",
    "a_directory",
    "a_stage",
    "an_account",
    "exec_form",
    "shell_form",
]


def shell_form(keyword: str, line: str, *, at: int = 0) -> Instruction:
    """`RUN pip install -r requirements.txt`, as the parser would hand it back."""
    return Instruction(keyword=keyword, form="shell", args=(line,), line=at)


def exec_form(keyword: str, *args: str, at: int = 0) -> Instruction:
    """`CMD ["python", "app.py"]`, as the parser would hand it back."""
    return Instruction(keyword=keyword, form="exec", args=args, line=at)


def a_directory(
    path: str, *, owner: tuple[int, int] = (0, 0), mode: int = 0o755, at: int = 0
) -> PathEntry:
    """A directory as `path_access` reports it, labelled with its numbers."""
    return PathEntry(
        path=path,
        uid=owner[0],
        gid=owner[1],
        mode=mode,
        directory=True,
        owner=f"{owner[0]}:{owner[1]}",
        line=at,
    )


def an_account(name: str, uid: int, *gids: int) -> Account:
    return Account(name=name, uid=uid, gids=frozenset(gids or (uid,)))


#: What an image with nothing in it says about any path: only `/`, root's.
ROOT = PathAccess(chain=(a_directory("/"),), exists=False)


def a_stage(
    base: str = "python:3.12-slim",
    *instructions: Instruction,
    name: str | None = None,
) -> Stage:
    return Stage(base=base, name=name, instructions=tuple(instructions))


class FakeBuildQuery:
    """Satisfies `practice.domain.ports.BuildQuery` from values held in memory."""

    def __init__(
        self,
        *,
        stages: Iterable[Stage] = (),
        process: Iterable[str] = (),
        user: str = "root",
        in_image: Iterable[str] = (),
        services: Mapping[str, Mapping[str, object]] | None = None,
        error: str | None = None,
        accounts: Iterable[Account] = (),
        paths: Mapping[str, PathAccess] | None = None,
    ) -> None:
        self._stages = tuple(stages)
        self._process = tuple(process)
        self._user = user
        self._in_image = frozenset(in_image)
        self._services = dict(services or {})
        self._error = error
        self._accounts = {account.name: account for account in accounts}
        self._paths = dict(paths or {})

    def error(self) -> str | None:
        return self._error

    def stages(self) -> tuple[Stage, ...]:
        return self._stages

    def effective_process(self) -> tuple[str, ...]:
        return self._process

    def final_user(self) -> str:
        return self._user

    def path_in_image(self, path: str) -> bool:
        return path in self._in_image

    def account(self, user: str | None = None) -> Account | None:
        if user is None and self._user == "root":
            return an_account("root", 0)
        return self._accounts.get(self._user if user is None else user)

    def path_access(self, path: str) -> PathAccess:
        return self._paths.get(path, ROOT)

    def services(self) -> frozenset[str]:
        return frozenset(self._services)

    def service(self, name: str) -> Mapping[str, object] | None:
        return self._services.get(name)
