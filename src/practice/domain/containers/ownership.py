"""Who may write where in the shipped image: the eleventh assertion, and its rule.

**Phase 24, and the reason the layer model learned ownership** (ADR 0030's
revisit list). *Permission denied as non-root* could not be written in Phase
23 because the only assertions that could grade it read the text, and the text
is not where the answer is. Measured on BuildKit: `WORKDIR /app/data` *after*
`USER app` creates the directory owned by `app`, so a check for `chown` before
`USER` fails a correct answer; and `COPY --chown=app:app . .` into a `/app`
that root's `WORKDIR` made leaves `/app` itself root's, so a check for
`--chown` passes one that crashes with `PermissionError`. Only the end state
tells those apart: who owns each directory, and with what mode.

`may` is the kernel's rule, written once and used twice: by `path_writable`
here, and by the adapter, which needs the same answer to know whether a
`mkdir` run as `app` would have stopped the build. **It is the rule, not an
approximation of it**: the owner's bits apply to the owner even when the
group's bits are wider, which is how `chmod 077` locks the owner out of their
own directory. Root passes every check, which is true for the access this
reads (write and search) and is the reason the exercise also asserts the
image does not run as root.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.domain.checks.evaluation import CheckResult
from practice.domain.containers.evaluation import NO_DEFINITION

if TYPE_CHECKING:
    from practice.domain.containers.evaluation import ContainerContext
    from practice.domain.ports import Account, PathAccess, PathEntry

__all__ = ["READ", "SEARCH", "WRITE", "may", "path_writable"]

READ: Final = 0o4
WRITE: Final = 0o2
#: The execute bit, which on a directory is permission to look inside it.
SEARCH: Final = 0o1


def may(account: Account, entry: PathEntry, want: int) -> bool:
    """Whether `account` has every bit of `want` on `entry`, as the kernel decides."""
    if account.uid == 0:
        return True
    if account.uid == entry.uid:
        bits = entry.mode >> 6
    elif entry.gid in account.gids:
        bits = entry.mode >> 3
    else:
        bits = entry.mode
    return bits & want == want


def path_writable(context: ContainerContext) -> CheckResult:
    """`path_writable {path, by?}` — the image's user can write to this path.

    The non-root lesson's end state: an app that writes `/app/data` has to be
    able to, as the user the image runs as. `by` asks about another account
    instead, and the advisory use of it is negated: `by: nobody` is how an
    exercise says *not by everyone*, which is what `chmod 777` does.

    **A path the image does not have is writable if it can be made**, which
    means write and search on the deepest directory it does have. That is what
    `mkdir -p` at start-up needs, and an answer that creates the directory
    owned by `app` is no more right than one that hands `app` its parent.
    """
    path = context.params.text("path")
    by = context.params.optional_text("by")
    query = context.query
    expected = f"{by or 'the user the image runs as'} can write {path}"
    if query.error() is not None:
        return CheckResult(passed=False, expected=expected, actual=NO_DEFINITION)
    passed, actual = _verdict(
        path, query.path_access(path), query.account(by), by or query.final_user()
    )
    return CheckResult(passed=passed, expected=expected, actual=actual)


def _verdict(
    path: str, access: PathAccess, account: Account | None, name: str
) -> tuple[bool, str]:
    if access.stopped is not None:
        return False, f"the build stops before there is an image: {access.stopped}"
    if account is None:
        return False, (
            f"the image has no user {name!r}, so `docker run` refuses to start "
            "it: no matching entries in passwd file"
        )
    if account.uid == 0:
        return True, f"it runs as {account.name!r}, uid 0, who can write anywhere"
    return _reach(path, access, account)


def _reach(path: str, access: PathAccess, account: Account) -> tuple[bool, str]:
    """The kernel's walk: search every directory above, then write the last."""
    *above, last = access.chain
    blocked = next((entry for entry in above if not may(account, entry, SEARCH)), None)
    if blocked is not None:
        return False, _refused(access, account, blocked, "enter")
    if not access.exists:
        if last.directory and may(account, last, WRITE | SEARCH):
            return True, (
                f"{path} does not exist yet, and {account.name!r} can create it "
                f"in {_describe(last)}"
            )
        return False, _refused(access, account, last, f"create {path} in")
    if may(account, last, WRITE | SEARCH if last.directory else WRITE):
        return True, f"{account.name!r} can write {_describe(last)}"
    return False, _refused(access, account, last, "write")


def _refused(access: PathAccess, account: Account, entry: PathEntry, verb: str) -> str:
    actual = f"{account.name!r} (uid {account.uid}) cannot {verb} {_describe(entry)}"
    return "; ".join((actual, *access.notes))


def _describe(entry: PathEntry) -> str:
    made = f", set on line {entry.line}" if entry.line else ", from the base image"
    return f"{entry.path} ({entry.owner}, mode {entry.mode:o}{made})"
