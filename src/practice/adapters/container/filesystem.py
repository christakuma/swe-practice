"""Who owns each path a Dockerfile creates, and which accounts the image has.

Phase 24's addition to the layer model (ADR 0030), behind `BuildQuery.account`
and `BuildQuery.path_access`. `build_query.py` tracks *which context files*
reach a stage; this module tracks the **owner and mode of every path the
definition creates**, and the `/etc/passwd` and `/etc/group` its `RUN` lines
build, because a uid is only comparable with a `USER` once both are numbers.

**Every rule here was measured on BuildKit (Docker 28.3, `python:3.12-slim`,
Debian 13)**, and four of them are not what the documentation suggests:

* `WORKDIR` creates every missing directory owned the way `--chown=<USER>`
  would own it, and leaves an existing one alone. `USER app` then `WORKDIR
  /srv/a/b` makes `/srv/a` and `/srv/a/b` `app`'s, and `/srv` stays root's.
  Under a `USER` the image does not have, `WORKDIR` makes it root's and does
  not complain; the next `RUN` is what fails.
* `COPY --chown` creates every missing parent of its destination owned by the
  `--chown` user too, and leaves an existing destination alone. `COPY
  --chown=app:app . .` into the `/app` a root `WORKDIR` made gives `app`
  every file and not the directory, so an app that creates `/app/data` still
  gets `PermissionError`. That is the exercise's most convincing wrong answer.
* `COPY` ignores `USER`: without `--chown` everything is `root:root`. `COPY
  --from` is the exception and keeps the source's owner and mode; the
  directory it copies *into* is still created root's.
* `--chmod` applies to the directories `COPY` creates as well as the files,
  masked by the 022 umask: `--chmod=777` makes them 755 and `--chmod=750`
  750.

The account commands follow Debian's allocators, which differ: `useradd` and
`groupadd` take one past the highest id in the range (so after `useradd -u
10001`, the next is 10002), while `adduser` and `addgroup` take the first free
one; system accounts count down from 999 for the first pair and up from 100
for the second. A user's own group reuses the uid when that gid is free.

**What it does not see**, which the port's docstring repeats: anything a
script or a command substitution does, and a base image's own accounts other
than Debian's. Every base is assumed to have `python:3.12-slim`'s, except
`scratch`, which has none. A `RUN` line that touches ownership in a way this
module cannot evaluate becomes a note that a failing verdict quotes, rather
than a silent guess either way; one that would fail the build is recorded as
where the build stops.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Final

from practice.adapters.container.dockerfile import (
    assignments,
    stage_index,
    substitute,
)
from practice.adapters.container.dockerignore import glob_matcher, normalise_path
from practice.domain.containers.ownership import SEARCH, WRITE, may
from practice.domain.ports import Account, PathAccess, PathEntry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

    from practice.domain.ports import Instruction, Stage

__all__ = ["Filesystem", "context_landings", "filesystems", "into_directory"]

_GLOB: Final = frozenset("*?[")
_UMASK: Final = 0o022
_DIRECTORY: Final = 0o755
#: What a file copied from the build context arrives with. Measured from a
#: Windows checkout; a Linux one gives 644. No assertion here can tell them
#: apart, since neither lets anyone but the owner write.
_CONTEXT_FILE: Final = 0o755
_HOME: Final = 0o700

#: `python:3.12-slim`'s `/etc/passwd` as (name, uid, gid), measured.
_BASE_USERS: Final = (
    ("root", 0, 0), ("daemon", 1, 1), ("bin", 2, 2), ("sys", 3, 3),
    ("sync", 4, 65534), ("games", 5, 60), ("man", 6, 12), ("lp", 7, 7),
    ("mail", 8, 8), ("news", 9, 9), ("uucp", 10, 10), ("proxy", 13, 13),
    ("www-data", 33, 33), ("backup", 34, 34), ("list", 38, 38), ("irc", 39, 39),
    ("_apt", 42, 65534), ("nobody", 65534, 65534),
)  # fmt: skip

#: Its `/etc/group`, measured. No base group has members.
_BASE_GROUPS: Final = (
    ("root", 0), ("daemon", 1), ("bin", 2), ("sys", 3), ("adm", 4), ("tty", 5),
    ("disk", 6), ("lp", 7), ("mail", 8), ("news", 9), ("uucp", 10), ("man", 12),
    ("proxy", 13), ("kmem", 15), ("dialout", 20), ("fax", 21), ("voice", 22),
    ("cdrom", 24), ("floppy", 25), ("tape", 26), ("sudo", 27), ("audio", 29),
    ("dip", 30), ("www-data", 33), ("backup", 34), ("operator", 37),
    ("list", 38), ("irc", 39), ("src", 40), ("shadow", 42), ("utmp", 43),
    ("video", 44), ("sasl", 45), ("plugdev", 46), ("staff", 50), ("games", 60),
    ("users", 100), ("nogroup", 65534),
)  # fmt: skip

#: The base image's directories, all root's, and the modes that are not 755.
_BASE_DIRECTORIES: Final = (
    "/", "/boot", "/dev", "/etc", "/home", "/media", "/mnt", "/opt", "/root",
    "/run", "/srv", "/tmp", "/usr", "/usr/local", "/var", "/var/cache",  # noqa: S108
    "/var/lib", "/var/local", "/var/log", "/var/opt", "/var/spool", "/var/tmp",  # noqa: S108
)  # fmt: skip
#: Paths in an image, not on this machine, so ruff's temp-file rule is beside the point.
_BASE_MODES: Final = {"/root": 0o700, "/tmp": 0o1777, "/var/tmp": 0o1777}  # noqa: S108

_USERS_GID: Final = 100
_NOGROUP: Final = 65534
_NORMAL: Final = range(1000, 60001)
_SYSTEM: Final = range(100, 1000)

#: Commands that change ownership, accounts or which paths exist -- and `cd`,
#: which changes what every relative path after it on the line means. One of
#: these that cannot be read becomes a note; any other command is assumed to
#: change none of them.
_WATCHED: Final = frozenset(
    {"adduser", "addgroup", "cd", "chgrp", "chmod", "chown", "groupadd",
     "install", "mkdir", "rm", "useradd", "usermod"}
)  # fmt: skip
_ACCOUNTS: Final = frozenset({"adduser", "addgroup", "groupadd", "useradd", "usermod"})
_SEPARATOR: Final = re.compile(r"&&|;|\n")
_PIPE: Final = re.compile(r"\|\|?")
_ASSIGNMENT: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
#: A redirection written as its own word: `>`, `2>/dev/null`, `2>&1`, `&>log`.
#: The target is in the word, or -- when nothing follows the operator, `>&`
#: included -- the next word.
_REDIRECT: Final = re.compile(r"^(?:\d*|&)(?:>>?|<)&?(.*)$")
_ID: Final = re.compile(r"[0-9]{1,10}")
_SYMBOLIC: Final = re.compile(r"^([ugoa]*)([-+=])([rwxXst]*)$")
_CLASS_BITS: Final = {"u": 0o4700, "g": 0o2070, "o": 0o1007, "a": 0o7777}
_PERM_BITS: Final = {"r": 0o444, "w": 0o222, "x": 0o111, "s": 0o6000, "t": 0o1000}

#: The account commands' options that take a value, short and long.
_VALUED: Final = frozenset(
    {"-b", "-c", "-d", "-e", "-f", "-g", "-G", "-k", "-K", "-p", "-R", "-P",
     "-s", "-u", "--base-dir", "--comment", "--home-dir", "--expiredate",
     "--inactive", "--gid", "--groups", "--skel", "--key", "--password",
     "--root", "--prefix", "--shell", "--uid", "--home", "--gecos",
     "--ingroup", "--firstuid", "--lastuid", "--firstgid", "--lastgid",
     "--conf"}
)  # fmt: skip
#: `mkdir`'s and `install`'s.
_FILE_VALUED: Final = frozenset({"-m", "-o", "-g", "--mode", "--owner", "--group"})

#: A context file and where in a stage's filesystem it ended up.
type Landing = tuple[str, str]


class _RefusedError(Exception):
    """A command in a `RUN` that would fail, and the reason, as one clause."""


@dataclass(slots=True)
class _User:
    uid: int
    gid: int
    groups: set[int] = field(default_factory=set)


@dataclass(slots=True)
class _Accounts:
    """The image's `/etc/passwd` and `/etc/group`, as far as this file built them."""

    users: dict[str, _User]
    groups: dict[str, int]

    @classmethod
    def base(cls, image: str) -> _Accounts:
        if image == "scratch":
            return cls(users={}, groups={})
        return cls(
            users={name: _User(uid, gid) for name, uid, gid in _BASE_USERS},
            groups=dict(_BASE_GROUPS),
        )

    def copy(self) -> _Accounts:
        return _Accounts(
            users={
                name: _User(user.uid, user.gid, set(user.groups))
                for name, user in self.users.items()
            },
            groups=dict(self.groups),
        )

    def account(self, spec: str) -> tuple[Account, int] | None:
        """What `USER spec` runs as, and its primary gid; `None` if refused.

        Measured: a name brings its supplementary groups, and so does a uid
        that `/etc/passwd` has. `user:group` runs with that group alone. A uid
        with no entry runs as group 0.
        """
        name, _, group = spec.partition(":")
        user = self._user(name)
        uid = user.uid if user is not None else _number(name)
        if uid is None:
            return None
        if group:
            gid = self.gid(group)
            if gid is None:
                return None
            gids = frozenset({gid})
        elif user is not None:
            gid = user.gid
            gids = frozenset({gid, *user.groups})
        else:
            gid, gids = 0, frozenset({0})
        return Account(name=name, uid=uid, gids=gids), gid

    def owner(self, spec: str, *, same_number: bool) -> tuple[int, int] | None:
        """A `chown` or `--chown` spec as numbers, `-1` for *unchanged*.

        `None` for a name the image does not have. A user alone keeps the
        group for `chown` (`same_number` false); for `--chown` and `WORKDIR` it
        takes the user's own group, or the same number for a bare uid, as
        Docker documents and as measured. `user:` and `user.` are `chown`'s
        spellings of *the user's own group*.
        """
        if not same_number and ":" not in spec and self._user(spec) is None:
            # `chown`'s `.` separator; Docker splits only on `:`, and an
            # account may be called `my.app`, so a whole-name match wins.
            spec = spec.replace(".", ":", 1)
        name, colon, group = spec.partition(":")
        uid = gid = -1
        if name:
            user = self._user(name)
            number = user.uid if user is not None else _number(name)
            if number is None:
                return None
            uid = number
            if (colon and not group) or (not colon and same_number):
                gid = user.gid if user is not None else uid
        if group:
            found = self.gid(group)
            if found is None:
                return None
            gid = found
        return uid, gid

    def gid(self, group: str) -> int | None:
        if group in self.groups:
            return self.groups[group]
        return _number(group)

    def label(self, uid: int, gid: int) -> str:
        user = next((n for n, u in self.users.items() if u.uid == uid), str(uid))
        group = next((n for n, g in self.groups.items() if g == gid), str(gid))
        return f"{user}:{group}"

    def _user(self, name: str) -> _User | None:
        if name in self.users:
            return self.users[name]
        uid = _number(name)
        if uid is not None:
            return next((u for u in self.users.values() if u.uid == uid), None)
        return None

    def add_user(  # noqa: PLR0913 - one account's six facts, read once
        self,
        name: str,
        *,
        uid: int | None,
        group: str | None,
        own_group: bool,
        extra: Iterable[str],
        system: bool,
        first_free: bool,
    ) -> _User:
        if name in self.users:
            raise _RefusedError(f"user {name!r} already exists")
        if uid is None:
            taken = {user.uid for user in self.users.values()}
            uid = _allocate(taken, system=system, first_free=first_free)
        if group is not None:
            gid = self.gid(group)
            if gid is None:
                raise _RefusedError(f"group {group!r} does not exist")
        elif own_group:
            if name in self.groups:
                raise _RefusedError(f"group {name} exists")
            used = set(self.groups.values())
            gid = (
                uid
                if uid not in used
                else _allocate(used, system=system, first_free=first_free)
            )
            self.groups[name] = gid
        else:
            # `useradd -N` joins `users`; `adduser --system` joins `nogroup`.
            gid = _NOGROUP if system and first_free else _USERS_GID
        user = _User(uid, gid, {self._group(each) for each in extra})
        self.users[name] = user
        return user

    def add_group(
        self, name: str, *, gid: int | None, system: bool, first_free: bool
    ) -> None:
        if name in self.groups:
            raise _RefusedError(f"group {name!r} already exists")
        if gid is None:
            used = set(self.groups.values())
            gid = _allocate(used, system=system, first_free=first_free)
        self.groups[name] = gid

    def join(self, name: str, groups: Iterable[str], *, append: bool = True) -> None:
        user = self.users.get(name)
        if user is None:
            raise _RefusedError(f"user {name!r} does not exist")
        joined = {self._group(group) for group in groups}
        user.groups = (user.groups | joined) if append else joined

    def _group(self, group: str) -> int:
        gid = self.gid(group)
        if gid is None:
            raise _RefusedError(f"group {group!r} does not exist")
        return gid


def _allocate(taken: set[int], *, system: bool, first_free: bool) -> int:
    """The next id Debian would hand out: see the module docstring."""
    span = _SYSTEM if system else _NORMAL
    if first_free:
        return next(i for i in span if i not in taken)
    if system:
        return next(i for i in reversed(span) if i not in taken)
    used = [i for i in taken if i in span]
    return max(used) + 1 if used else span.start


@dataclass(frozen=True, slots=True)
class _Node:
    uid: int
    gid: int
    mode: int
    directory: bool
    line: int = 0


@dataclass(slots=True)
class Filesystem:
    """One stage's paths and accounts at its end, and what could not be applied.

    **`workdir` and `env` are here rather than on the walk** because a stage
    built `FROM` an earlier one inherits both, as it inherits `user`: the
    first version reset them per stage, so `WORKDIR /app` in a base stage
    and `RUN mkdir data` in the stage built on it made `/data`, while
    `build_query.py`'s layer model -- which does inherit the workdir -- put
    the same stage's files under `/app`. `ARG` is not here: Docker scopes a
    build argument to the stage that declares it.
    """

    nodes: dict[str, _Node]
    accounts: _Accounts
    user: str
    notes: list[str] = field(default_factory=list)
    stopped: str | None = None
    workdir: str = "/"
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def base(cls, image: str) -> Filesystem:
        directories = ("/",) if image == "scratch" else _BASE_DIRECTORIES
        return cls(
            nodes={
                path: _Node(0, 0, _BASE_MODES.get(path, _DIRECTORY), directory=True)
                for path in directories
            },
            accounts=_Accounts.base(image),
            user="root",
        )

    def copy(self) -> Filesystem:
        return Filesystem(
            nodes=dict(self.nodes),
            accounts=self.accounts.copy(),
            user=self.user,
            notes=list(self.notes),
            stopped=self.stopped,
            workdir=self.workdir,
            env=dict(self.env),
        )

    def account(self, spec: str | None = None) -> Account | None:
        resolved = self.accounts.account(self.user if spec is None else spec)
        return resolved[0] if resolved is not None else None

    def access(self, path: str) -> PathAccess:
        target = posixpath.normpath(posixpath.join("/", path))
        chain: list[PathEntry] = []
        for spot in _self_and_parents(target):
            if spot not in self.nodes:
                break
            chain.append(self.entry(spot))
        return PathAccess(
            chain=tuple(chain),
            exists=chain[-1].path == target,
            notes=tuple(self.notes),
            stopped=self.stopped,
        )

    def entry(self, path: str) -> PathEntry:
        node = self.nodes[path]
        return PathEntry(
            path=path,
            uid=node.uid,
            gid=node.gid,
            mode=node.mode,
            directory=node.directory,
            owner=self.accounts.label(node.uid, node.gid),
            line=node.line,
        )

    def make(  # noqa: PLR0913 - a path, its owner and mode, and its parents'
        self,
        path: str,
        *,
        owner: tuple[int, int],
        mode: int,
        line: int,
        directory: bool = True,
        parents_mode: int = _DIRECTORY,
        parents_owner: tuple[int, int] | None = None,
    ) -> None:
        """Create `path` and its missing parents, leaving existing directories alone.

        A file is always written, because a `COPY` over a file replaces it.
        """
        *parents, last = _self_and_parents(path)
        above = parents_owner if parents_owner is not None else owner
        for spot in parents:
            if spot not in self.nodes:
                self.nodes[spot] = _Node(*above, parents_mode, True, line)
        if directory and last in self.nodes and self.nodes[last].directory:
            return
        self.nodes[last] = _Node(*owner, mode, directory, line)

    def under(self, path: str) -> list[str]:
        below = path.rstrip("/") + "/"
        return [spot for spot in self.nodes if spot == path or spot.startswith(below)]

    def stop(self, sentence: str) -> None:
        """Record the first command that fails the build. Nothing after it runs."""
        if self.stopped is None:
            self.stopped = sentence


def filesystems(stages: Sequence[Stage], files: Sequence[str]) -> list[Filesystem]:
    """Every stage's filesystem at its end, each built on the stage it is `FROM`."""
    results: list[Filesystem] = []
    for index, stage in enumerate(stages):
        parent = stage_index(stages[:index], stage.base)
        fs = (
            results[parent].copy()
            if parent is not None
            else Filesystem.base(stage.base)
        )
        _Walk(fs, stages[:index], results, files).stage(stage)
        results.append(fs)
    return results


@dataclass(slots=True)
class _Walk:
    """One stage's instructions applied in order to its filesystem."""

    fs: Filesystem
    earlier_stages: Sequence[Stage]
    earlier: Sequence[Filesystem]
    files: Sequence[str]
    #: This stage's `ARG`s, which end with it; `ENV` is the filesystem's.
    args: dict[str, str] = field(default_factory=dict)
    #: The shell's directory: the `WORKDIR`, until a `cd` inside a `RUN` line
    #: moves it for the rest of that line.
    cwd: str = "/"

    @property
    def variables(self) -> dict[str, str]:
        """What `$NAME` expands to. `ENV` wins over an `ARG` of the same name."""
        return {**self.args, **self.fs.env}

    def stage(self, stage: Stage) -> None:
        self.cwd = self.fs.workdir
        for instruction in stage.instructions:
            if self.fs.stopped is not None:
                return
            match instruction.keyword:
                case "USER" if instruction.args:
                    self.fs.user = substitute(instruction.args[0], self.variables)
                case "ARG":
                    self.args.update(assignments(instruction))
                case "ENV":
                    self.fs.env.update(assignments(instruction))
                case "WORKDIR" if instruction.args:
                    self._workdir(instruction)
                case "COPY" | "ADD" if instruction.args[1:]:
                    self._copy(instruction)
                case "RUN" if instruction.args:
                    self._run(instruction)
                case _:
                    pass

    def _is_directory(self, path: str) -> bool:
        node = self.fs.nodes.get(path)
        return node is not None and node.directory

    def _resolve(self, path: str) -> str:
        return posixpath.normpath(posixpath.join(self.cwd, path))

    def _workdir(self, instruction: Instruction) -> None:
        self.fs.workdir = self._resolve(substitute(instruction.args[0], self.variables))
        self.cwd = self.fs.workdir
        owner = self.fs.accounts.owner(self.fs.user, same_number=True) or (0, 0)
        self.fs.make(
            self.fs.workdir, owner=owner, mode=_DIRECTORY, line=instruction.line
        )

    # --- COPY and ADD ---------------------------------------------------

    def _copy(self, instruction: Instruction) -> None:
        flags = dict(instruction.flags)
        line = instruction.line
        owner: tuple[int, int] | None = None
        if "chown" in flags:
            spec = substitute(flags["chown"], self.variables)
            owner = self.fs.accounts.owner(spec, same_number=True)
            if owner is None:
                self.fs.stop(
                    f"line {line}: --chown={spec} names an account the image "
                    "does not have"
                )
                return
        mode: int | None = None
        if "chmod" in flags:
            mode = _octal(flags["chmod"])
            if mode is None:
                self._unread(line, f"--chmod={flags['chmod']}")
        made = mode & ~_UMASK if mode is not None else _DIRECTORY
        *sources, dest = instruction.args
        target = self._resolve(dest)
        if "from" not in flags:
            if any("://" in source for source in sources):
                return
            landed = owner or (0, 0)
            landings = context_landings(
                instruction, self.files, self.fs.workdir, self._is_directory
            )
            for _, spot in landings:
                self.fs.make(
                    spot,
                    owner=landed,
                    mode=mode if mode is not None else _CONTEXT_FILE,
                    line=line,
                    directory=False,
                    parents_mode=made,
                )
            if dest.endswith("/") or len(sources) > 1:
                self.fs.make(target, owner=landed, mode=made, line=line)
            return
        index = stage_index(self.earlier_stages, flags["from"])
        origin = self.earlier[index] if index is not None else None
        for raw in sources:
            copied = _Copied(owner=owner, mode=mode, made=made, line=line)
            self._from_stage(origin, raw, dest, target, copied)

    def _from_stage(
        self,
        origin: Filesystem | None,
        raw: str,
        dest: str,
        target: str,
        copied: _Copied,
    ) -> None:
        """`COPY --from`: the source's owner and mode, unless the flags override.

        A source the model never saw, such as a `dist/` a builder's `RUN`
        produced, is taken to be a directory and lands as one, owned as
        `--chown` says or by root. That is the reading under which nothing it
        holds is refused: `COPY --from=build --chown=app /src/dist /app` gives
        `app` a directory, and calling it a file would fail that answer.
        """
        source = posixpath.normpath(posixpath.join("/", raw))
        found = origin.nodes.get(source) if origin is not None else None
        line = copied.line
        if found is not None and not found.directory:
            inside = into_directory(
                dest, target, many=False, is_directory=self._is_directory
            )
            spot = (
                posixpath.join(target, posixpath.basename(source)) if inside else target
            )
            self.fs.make(
                spot,
                owner=copied.owner or (found.uid, found.gid),
                mode=copied.choose(found.mode),
                line=line,
                directory=False,
                parents_mode=copied.made,
            )
            return
        self.fs.make(target, owner=copied.owner or (0, 0), mode=copied.made, line=line)
        if origin is None or found is None:
            return
        for spot in origin.under(source):
            if spot == source:
                continue
            node = origin.nodes[spot]
            uid, gid = copied.owner or (node.uid, node.gid)
            # `lstrip` rather than skipping one more character: when the
            # source is `/` there is no separator after it to skip, and
            # `/app` landed at `<target>/pp`. `_from_stage` in
            # `build_query.py` cuts the same way.
            relative = spot[len(source) :].lstrip("/")
            self.fs.nodes[posixpath.join(target, relative)] = _Node(
                uid, gid, copied.choose(node.mode), node.directory, line
            )

    # --- RUN ------------------------------------------------------------

    def _run(self, instruction: Instruction) -> None:
        line = instruction.line
        resolved = self.fs.accounts.account(self.fs.user)
        if resolved is None:
            self.fs.stop(
                f"line {line} runs as {self.fs.user!r}, and the image has no "
                "such user: unable to find user"
            )
            return
        if instruction.form == "exec":
            commands = [(list(instruction.args), False)]
        else:
            commands = self._commands(instruction.args[0], line)
        try:
            for words, guarded in commands:
                if not words or words[0] not in _WATCHED:
                    continue
                try:
                    self._command(words, *resolved, line)
                except _RefusedError as refused:
                    if not guarded:
                        self.fs.stop(
                            f"line {line}: `{' '.join(words)}` fails: {refused}"
                        )
                        return
        finally:
            # A `cd` lasts as long as the shell, which is this one line.
            self.cwd = self.fs.workdir

    def _commands(self, text: str, line: int) -> list[tuple[list[str], bool]]:
        """The simple commands of a shell line, and whether a failure is caught.

        Split on `&&`, `;` and newlines. A command after `||` or `|` is
        dropped: it runs only if the one before it failed, or with that one's
        output. The one before a `||` is *guarded*: if it would fail, the
        build carries on without its effect, as `mkdir /x || true` does.
        """
        commands: list[tuple[list[str], bool]] = []
        for piece in _SEPARATOR.split(text):
            guarded = "||" in piece
            command = _PIPE.split(piece)[0]
            words = command.split()
            if not words:
                continue
            if words[0] in _WATCHED and ("$(" in command or "`" in command):
                self.fs.notes.append(
                    f"line {line} runs {words[0]} with a command substitution, "
                    "which the grader cannot evaluate"
                )
                continue
            try:
                words = shlex.split(substitute(command, self.variables))
            except ValueError:
                continue
            while words and _ASSIGNMENT.fullmatch(words[0]):
                words = words[1:]
            commands.append((_without_redirections(words), guarded))
        return commands

    def _cd(self, operands: Sequence[str], line: int) -> None:
        """Move the shell for the rest of the line, as `RUN cd /app && ...` does.

        A directory the model has not seen is followed anyway: a script may
        have made it, and the paths after the `cd` are better read against it
        than against a `WORKDIR` the line has left. `cd` alone, `cd -` and `~`
        depend on the shell's own state and are noted rather than guessed.
        """
        target = operands[0] if operands else ""
        if not target or target == "-" or target.startswith("~"):
            self.fs.notes.append(
                f"line {line} runs `cd {target}`, which the grader cannot follow; "
                f"the paths after it are read from {self.cwd}"
            )
            return
        self.cwd = self._resolve(target)

    def _command(self, words: list[str], account: Account, gid: int, line: int) -> None:
        name, *rest = words
        if name in _ACCOUNTS:
            if account.uid != 0:
                raise _RefusedError("only root can change the image's accounts")
            _ACCOUNT_COMMANDS[name](self, rest, line)
            return
        options, operands = _options(rest, valued=_FILE_VALUED, modes=name == "chmod")
        match name:
            case "cd":
                self._cd(operands, line)
            case "mkdir":
                self._mkdir(options, operands, account, gid, line)
            case "install" if _has(options, "-d", "--directory"):
                self._install(options, operands, account, gid, line)
            case "chown" | "chgrp" | "chmod" if operands[1:]:
                recursive = _has(options, "-R", "--recursive")
                spec, *paths = operands
                for path in self._targets(paths, recursive=recursive, line=line):
                    if name == "chmod":
                        self._chmod(spec, path, account, line)
                    else:
                        owner = spec if name == "chown" else ":" + spec
                        self._chown(owner, path, account, line)
            case "rm":
                self._rm(operands)
            case _:
                pass

    def _rm(self, operands: Sequence[str]) -> None:
        for operand in operands:
            for spot in self.fs.under(self._resolve(operand)):
                # `rm -rf /` empties the image and leaves its root.
                if spot != "/":
                    del self.fs.nodes[spot]

    def _mkdir(
        self,
        options: Mapping[str, str],
        operands: Sequence[str],
        account: Account,
        gid: int,
        line: int,
    ) -> None:
        """`mkdir [-p] [-m MODE]`: `-m` is the last directory's, parents get 755."""
        mode = self._given_mode(options, line)
        parents = _has(options, "-p", "--parents")
        for operand in operands:
            path = self._resolve(operand)
            if path in self.fs.nodes:
                if parents:
                    continue
                raise _RefusedError(f"cannot create {path}: File exists")
            self._may_create(path, account, parents=parents)
            self.fs.make(path, owner=(account.uid, gid), mode=mode, line=line)

    def _install(
        self,
        options: Mapping[str, str],
        operands: Sequence[str],
        account: Account,
        gid: int,
        line: int,
    ) -> None:
        """`install -d [-o USER] [-g GROUP] [-m MODE]`, which sets all three
        on the directories it names, whether or not they existed, and creates
        missing parents as the build user would."""
        user = _get(options, "-o", "--owner")
        group = _get(options, "-g", "--group")
        owner = (account.uid, gid)
        if user is not None or group is not None:
            if account.uid != 0:
                raise _RefusedError("Operation not permitted")
            spec = (user or "") + (f":{group}" if group else "")
            found = self.fs.accounts.owner(spec, same_number=False)
            if found is None:
                raise _RefusedError(f"invalid user or group {spec!r}")
            owner = (
                found[0] if found[0] >= 0 else owner[0],
                found[1] if found[1] >= 0 else owner[1],
            )
        mode = self._given_mode(options, line)
        for operand in operands:
            path = self._resolve(operand)
            self._may_create(path, account, parents=True)
            self.fs.make(
                path,
                owner=owner,
                mode=mode,
                line=line,
                parents_owner=(account.uid, gid),
            )
            self.fs.nodes[path] = _Node(*owner, mode, True, line)

    def _may_create(self, path: str, account: Account, *, parents: bool) -> None:
        """Refuse a `mkdir` the build user could not run, as the kernel would."""
        for spot in _self_and_parents(path)[1:]:
            if spot in self.fs.nodes:
                continue
            above = posixpath.dirname(spot)
            if spot != path and not parents:
                raise _RefusedError(f"cannot create {path}: No such file or directory")
            if not may(account, self.fs.entry(above), WRITE | SEARCH):
                raise _RefusedError(f"{account.name} cannot write {above}")
            return

    def _targets(
        self, operands: Sequence[str], *, recursive: bool, line: int
    ) -> list[str]:
        """The tracked paths a `chown` or `chmod` changes.

        A path this model has not seen is taken to be a directory the base
        image has, root's and 755: a `chown` of a path that does not exist
        stops the build, so treating it as absent would grade no answer at all.
        """
        targets: list[str] = []
        for operand in operands:
            path = self._resolve(operand)
            if path not in self.fs.nodes:
                self.fs.make(path, owner=(0, 0), mode=_DIRECTORY, line=line)
            targets.extend(self.fs.under(path) if recursive else [path])
        return targets

    def _chown(self, spec: str, path: str, account: Account, line: int) -> None:
        owner = self.fs.accounts.owner(spec, same_number=False)
        if owner is None:
            raise _RefusedError(f"invalid user or group {spec!r}")
        node = self.fs.nodes[path]
        uid = node.uid if owner[0] < 0 else owner[0]
        gid = node.gid if owner[1] < 0 else owner[1]
        # Measured: `chown` as anyone but root is `Operation not permitted`,
        # except giving your own file to one of your own groups.
        if account.uid != 0 and (
            uid != account.uid or node.uid != account.uid or gid not in account.gids
        ):
            raise _RefusedError(
                f"changing ownership of {path}: Operation not permitted"
            )
        self.fs.nodes[path] = replace(node, uid=uid, gid=gid, line=line)

    def _chmod(self, spec: str, path: str, account: Account, line: int) -> None:
        node = self.fs.nodes[path]
        if account.uid not in {0, node.uid}:
            raise _RefusedError(
                f"changing permissions of {path}: Operation not permitted"
            )
        mode = _parsed_mode(spec, node.mode, umask=_UMASK, directory=node.directory)
        if mode is None:
            self._unread(line, f"chmod {spec}")
            return
        self.fs.nodes[path] = replace(node, mode=mode, line=line)

    def _unread(self, line: int, what: str) -> None:
        self.fs.notes.append(
            f"line {line}: the grader cannot read `{what}`, so it was not applied"
        )

    def _given_mode(self, options: Mapping[str, str], line: int) -> int:
        given = _get(options, "-m", "--mode")
        if given is None:
            return _DIRECTORY
        mode = _parsed_mode(given, 0o777, umask=0)
        if mode is None:
            self._unread(line, f"-m {given}")
            return _DIRECTORY
        return mode

    # --- accounts -------------------------------------------------------

    def _useradd(self, words: Sequence[str], line: int) -> None:
        options, operands = _options(words, valued=_VALUED)
        if not operands:
            return
        name = operands[-1]
        group = _get(options, "-g", "--gid")
        user = self.fs.accounts.add_user(
            name,
            uid=_number(_get(options, "-u", "--uid")),
            group=group,
            own_group=group is None and not _has(options, "-N", "--no-user-group"),
            extra=_split(_get(options, "-G", "--groups")),
            system=_has(options, "-r", "--system"),
            first_free=False,
        )
        if _has(options, "-m", "--create-home"):
            self._home(_get(options, "-d", "--home-dir") or f"/home/{name}", user, line)

    def _adduser(self, words: Sequence[str], line: int) -> None:
        options, operands = _options(words, valued=_VALUED)
        if len(operands) == 2:  # noqa: PLR2004 - `adduser USER GROUP` joins one
            self.fs.accounts.join(operands[0], [operands[1]])
            return
        if not operands:
            return
        name = operands[0]
        system = "--system" in options
        group = options.get("--ingroup") or options.get("--gid")
        user = self.fs.accounts.add_user(
            name,
            uid=_number(options.get("--uid")),
            group=group,
            own_group=group is None and (not system or "--group" in options),
            extra=() if system else ("users",),
            system=system,
            first_free=True,
        )
        if not system and "--no-create-home" not in options:
            self._home(options.get("--home") or f"/home/{name}", user, line)

    def _home(self, home: str, user: _User, line: int) -> None:
        """Measured: a home is 700 and the user's, whatever made it, and its
        parents are root's."""
        path = self._resolve(home)
        owner = (user.uid, user.gid)
        self.fs.make(path, owner=owner, mode=_HOME, line=line, parents_owner=(0, 0))
        self.fs.nodes[path] = _Node(*owner, _HOME, True, line)

    def _groupadd(self, words: Sequence[str], _line: int) -> None:
        options, operands = _options(words, valued=_VALUED)
        if operands:
            self.fs.accounts.add_group(
                operands[-1],
                gid=_number(_get(options, "-g", "--gid")),
                system=_has(options, "-r", "--system"),
                first_free=False,
            )

    def _addgroup(self, words: Sequence[str], _line: int) -> None:
        options, operands = _options(words, valued=_VALUED)
        if len(operands) == 2:  # noqa: PLR2004 - `addgroup USER GROUP` joins one
            self.fs.accounts.join(operands[0], [operands[1]])
        elif operands:
            self.fs.accounts.add_group(
                operands[0],
                gid=_number(options.get("--gid")),
                system="--system" in options,
                first_free=True,
            )

    def _usermod(self, words: Sequence[str], _line: int) -> None:
        options, operands = _options(words, valued=_VALUED)
        groups = _get(options, "-G", "--groups")
        if groups is not None and operands:
            self.fs.accounts.join(
                operands[-1],
                _split(groups),
                append=_has(options, "-a", "--append"),
            )


@dataclass(frozen=True, slots=True)
class _Copied:
    """What one `COPY --from` does to ownership: its flags, resolved once."""

    owner: tuple[int, int] | None
    mode: int | None
    made: int
    line: int

    def choose(self, kept: int) -> int:
        return kept if self.mode is None else self.mode


_ACCOUNT_COMMANDS: Final[Mapping[str, Callable[[_Walk, Sequence[str], int], None]]] = {
    "useradd": _Walk._useradd,  # noqa: SLF001
    "adduser": _Walk._adduser,  # noqa: SLF001
    "groupadd": _Walk._groupadd,  # noqa: SLF001
    "addgroup": _Walk._addgroup,  # noqa: SLF001
    "usermod": _Walk._usermod,  # noqa: SLF001
}


def into_directory(
    dest: str, target: str, *, many: bool, is_directory: Callable[[str], bool]
) -> bool:
    """Whether a `COPY` puts its sources *inside* `dest` rather than *at* it.

    Docker's rule, all three halves of it: a trailing slash, more than one
    source, or a destination that already exists as a directory. The last is
    the one `COPY app.py .` relies on, because `.` is the `WORKDIR`. The first
    version knew only the first two and landed the file *at* `/app`: the layer
    model then lost a secret a later `COPY --from=build /app/.env` carried, and
    this model would have turned the `WORKDIR` itself into a file. Both models
    ask it, each with its own idea of which directories exist.
    """
    return dest.endswith("/") or many or is_directory(target)


def context_landings(
    instruction: Instruction,
    files: Sequence[str],
    workdir: str,
    is_directory: Callable[[str], bool],
) -> set[Landing]:
    """Where each build-context file a `COPY` or `ADD` names lands in the stage."""
    *sources, dest = instruction.args
    target = posixpath.normpath(posixpath.join(workdir, dest))
    inside = into_directory(
        dest, target, many=len(sources) > 1, is_directory=is_directory
    )
    landed: set[Landing] = set()
    for raw in sources:
        source = normalise_path(raw)
        source = "" if source == "." else source
        # Docker's matcher, not `fnmatch`: `*` stops at a slash, so `*.py` copies
        # the top-level modules and not `pkg/models.py`. `fnmatch` lets `*`
        # cross directories, and the first version of this reported files in
        # the image that a real build leaves out.
        glob = glob_matcher(source) if _GLOB & set(source) else None
        for path in files:
            if not source:
                landed.add((path, posixpath.join(target, path)))
            elif path == source or (glob is not None and glob.fullmatch(path)):
                name = posixpath.basename(path)
                spot = (
                    posixpath.join(target, name)
                    if inside or glob is not None
                    else target
                )
                landed.add((path, spot))
            elif path.startswith(source + "/"):
                landed.add((path, posixpath.join(target, path[len(source) + 1 :])))
    return landed


def _without_redirections(words: Sequence[str]) -> list[str]:
    """A command's words with its redirections and their targets taken out.

    The shell removes them before the command sees its arguments, and left
    in they were operands: `mkdir /r 2>/dev/null`, run from `/`, also asked
    for `/2>/dev/null`, whose parent `/2>` does not exist, and that stopped
    a build that runs.
    """
    kept: list[str] = []
    iterator = iter(words)
    for word in iterator:
        found = _REDIRECT.match(word)
        if found is None:
            kept.append(word)
        elif not found.group(1):
            next(iterator, None)
    return kept


def _self_and_parents(path: str) -> list[str]:
    """`/a/b` as `["/", "/a", "/a/b"]`."""
    parts = [part for part in path.split("/") if part]
    return ["/"] + ["/" + "/".join(parts[: end + 1]) for end in range(len(parts))]


def _options(
    words: Sequence[str], *, valued: frozenset[str], modes: bool = False
) -> tuple[dict[str, str], list[str]]:
    """Options and their values, and the operands among them.

    `-pm 755` and `--mode=755` are read as `mkdir` reads them: a short cluster
    is split into letters, the first that takes a value takes the rest of the
    word or the next one. For `chmod` (`modes`), `-w` is a mode, not an option.
    """
    options: dict[str, str] = {}
    operands: list[str] = []
    iterator = iter(words)
    for word in iterator:
        if word == "--":
            operands.extend(iterator)
        elif word.startswith("--"):
            key, equals, value = word.partition("=")
            options[key] = value if equals or key not in valued else next(iterator, "")
        elif (
            word.startswith("-")
            and word != "-"
            and not (modes and _SYMBOLIC.match(word))
        ):
            for position, letter in enumerate(word[1:], start=2):
                flag = "-" + letter
                if flag in valued:
                    options[flag] = word[position:] or next(iterator, "")
                    break
                options[flag] = ""
        else:
            operands.append(word)
    return options, operands


def _has(options: Mapping[str, str], short: str, long: str) -> bool:
    return short in options or long in options


def _get(options: Mapping[str, str], short: str, long: str) -> str | None:
    return options.get(short, options.get(long))


def _split(groups: str | None) -> list[str]:
    return [group for group in (groups or "").split(",") if group]


def _number(text: str | None) -> int | None:
    """A uid or gid as written: ASCII digits, at most ten, which is 2**32.

    Not `str.isdigit`, which is true of `²` and of a five-thousand-digit
    string, and `int` raises on both. This runs in `ParsedBuildQuery`'s
    constructor, so `USER ²` was a crash in grading rather than a user the
    image does not have.
    """
    return int(text) if text is not None and _ID.fullmatch(text) else None


def _octal(text: str) -> int | None:
    return int(text, 8) if re.fullmatch(r"[0-7]{1,4}", text) else None


def _parsed_mode(
    spec: str, current: int, *, umask: int, directory: bool = True
) -> int | None:
    """A `chmod` mode applied to `current`, or `None` for one it cannot read.

    Octal, or `u+w,o-rwx` clauses. A clause with no `ugoa` honours the umask,
    as `chmod` does: under 022, `chmod +w` adds only the owner's write bit and
    `o+w` adds the others' (measured). Copying bits (`g=u`) is left unread
    and noted rather than guessed at; `chmod` itself would run it.
    """
    octal = _octal(spec)
    if octal is not None:
        return octal
    mode = current
    for clause in spec.split(","):
        found = _SYMBOLIC.match(clause)
        if found is None:
            return None
        who, operator, perms = found.groups()
        clear = 0
        for letter in who or "a":
            clear |= _CLASS_BITS[letter]
        mask = clear if who else clear & ~umask
        bits = 0
        for letter in perms:
            if letter == "X":
                bits |= 0o111 if directory or current & 0o111 else 0
            else:
                bits |= _PERM_BITS[letter]
        bits &= mask
        if operator == "+":
            mode |= bits
        elif operator == "-":
            mode &= ~bits
        else:
            mode = (mode & ~clear) | bits
    return mode
