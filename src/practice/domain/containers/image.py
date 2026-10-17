"""What the image is built from, how, and what it runs. Seven of the eight assertions.

Every one reads what Docker *does* with a Dockerfile rather than what the file
says, and that is the line between this module and a linter. `pid1_matches`
asks the port for the composed process rather than looking for `CMD [`, so
`ENTRYPOINT ["python"]` with `CMD ["app.py"]` passes and `CMD ["sh", "-c",
"python app.py"]` fails, though the second has brackets and the first has
no `CMD` worth the name. `path_in_image` follows the build context through
`.dockerignore` and ignores `RUN rm`, because the layer that copied a file
still holds it. A text match could see neither.

**Patterns are unanchored and case-sensitive**, the git family's rule rather
than the drill family's case-insensitive one. Image names, flags and paths are
case-sensitive to Docker, and `-B` is not `-b`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult, matcher
from practice.domain.containers.evaluation import NO_DEFINITION, quote, stage_of

if TYPE_CHECKING:
    from practice.domain.containers.evaluation import ContainerContext

__all__ = [
    "base_image_matches",
    "command_matches",
    "instruction_matches",
    "ordered_before",
    "path_in_image",
    "pid1_matches",
    "runs_as",
]


def base_image_matches(context: ContainerContext) -> CheckResult:
    """`base_image_matches {pattern, stage?}` — the stage is built `FROM` this.

    The pinning lesson. `python:3.12-slim` and `python:latest` both build today;
    only one of them builds the same thing next month. A pattern rather than a
    list of allowed tags, so an author can ask for *a* pinned slim Python
    (`^python:3\\.\\d+(\\.\\d+)?-slim`) without enumerating releases.
    """
    pattern = matcher(context.params)
    stage, where = stage_of(context)
    expected = f"{where} built FROM an image matching {pattern.pattern!r}"
    if stage is None:
        return CheckResult(passed=False, expected=expected, actual=_missing(context))
    return CheckResult(
        passed=pattern.search(stage.base) is not None,
        expected=expected,
        actual=f"FROM {stage.base}",
    )


def ordered_before(context: ContainerContext) -> CheckResult:
    """`ordered_before {first, then, stage?}` — an instruction comes before another.

    The layer-cache lesson, and the only assertion here about order. `first`
    and `then` are patterns over whole instructions (`^COPY .*requirements`,
    `^RUN .*pip install`), and the check is that the **first** instruction
    matching `first` precedes the first matching `then`. Both have to be
    present: a Dockerfile with no `pip install` at all has not ordered it
    well, it has left it out, and passing it would be vacuous.
    """
    first = matcher(context.params, "first")
    then = matcher(context.params, "then")
    stage, where = stage_of(context)
    expected = (
        f"in {where}, an instruction matching {first.pattern!r} before one "
        f"matching {then.pattern!r}"
    )
    if stage is None:
        return CheckResult(passed=False, expected=expected, actual=_missing(context))

    texts = [instruction.text for instruction in stage.instructions]
    at_first = next((i for i, text in enumerate(texts) if first.search(text)), None)
    at_then = next((i for i, text in enumerate(texts) if then.search(text)), None)
    if at_first is None or at_then is None:
        absent = first if at_first is None else then
        return CheckResult(
            passed=False,
            expected=expected,
            actual=f"no instruction matches {absent.pattern!r}",
        )
    return CheckResult(
        passed=at_first < at_then,
        expected=expected,
        actual=(
            f"{quote(texts[at_first])!r} is instruction {at_first + 1}, "
            f"{quote(texts[at_then])!r} is instruction {at_then + 1}"
        ),
    )


def pid1_matches(context: ContainerContext) -> CheckResult:
    """`pid1_matches {pattern}` — the program the container starts as PID 1.

    The signals lesson, and the reason the port composes the process rather
    than handing back `CMD`. PID 1 is whatever runs first: a shell-form `CMD`
    makes it `/bin/sh`, which does not forward `SIGTERM` to its child, so
    `docker stop` waits out its ten seconds and sends `SIGKILL`. Usually
    written negated, with a pattern for a shell, because the lesson is
    *not a shell* rather than *this exact binary*.
    """
    pattern = matcher(context.params)
    process = context.query.effective_process()
    expected = f"PID 1 is a program matching {pattern.pattern!r}"
    if not process:
        return CheckResult(passed=False, expected=expected, actual=_no_process(context))
    return CheckResult(
        passed=pattern.search(process[0]) is not None,
        expected=expected,
        actual=f"PID 1 is {process[0]!r}, started as {quote(' '.join(process))!r}",
    )


def command_matches(context: ContainerContext) -> CheckResult:
    """`command_matches {pattern}` — the container's whole start command matches.

    The argument vector joined with spaces, `ENTRYPOINT` and `CMD` composed,
    so a bind address can be asserted wherever the solver put it. That is where
    the reachability lesson lives: `0.0.0.0` inside the container is every
    interface, and `127.0.0.1` is only the container's own loopback, which a
    published port never reaches.
    """
    pattern = matcher(context.params)
    process = context.query.effective_process()
    expected = f"the start command matches {pattern.pattern!r}"
    if not process:
        return CheckResult(passed=False, expected=expected, actual=_no_process(context))
    line = " ".join(process)
    return CheckResult(
        passed=pattern.search(line) is not None,
        expected=expected,
        actual=f"the container starts {quote(line)!r}",
    )


def runs_as(context: ContainerContext) -> CheckResult:
    """`runs_as {pattern}` — the user the shipped image runs as.

    Usually negated with `^(root|0)(:|$)`, which is the honest statement of the
    lesson. Asking for one particular user name would fail every solver who
    called theirs `app` instead of `appuser`.
    """
    pattern = matcher(context.params)
    expected = f"the image runs as a user matching {pattern.pattern!r}"
    if context.query.error() is not None:
        return CheckResult(passed=False, expected=expected, actual=NO_DEFINITION)
    user = context.query.final_user()
    return CheckResult(
        passed=pattern.search(user) is not None,
        expected=expected,
        actual=f"it runs as {user!r}",
    )


def instruction_matches(context: ContainerContext) -> CheckResult:
    """`instruction_matches {pattern, stage?}` — some instruction in the stage matches.

    The general-purpose assertion, and the one most worth reading negated:
    `not: true` with `^RUN .*rm .*\\.env` is how an exercise says *that line
    does not do what you think*. Reports the instruction that matched, because
    the negated form is the common one and *nothing matched* tells a solver
    nothing next to the line that did.
    """
    pattern = matcher(context.params)
    stage, where = stage_of(context)
    expected = f"an instruction in {where} matching {pattern.pattern!r}"
    if stage is None:
        return CheckResult(passed=False, expected=expected, actual=_missing(context))
    for instruction in stage.instructions:
        if pattern.search(instruction.text):
            return CheckResult(
                passed=True,
                expected=expected,
                actual=f"line {instruction.line}: {quote(instruction.text)!r}",
            )
    return CheckResult(
        passed=False, expected=expected, actual=f"no instruction in {where} matches"
    )


def path_in_image(context: ContainerContext) -> CheckResult:
    """`path_in_image {path}` — a build-context file ends up in the shipped image.

    The secrets lesson, written negated: `.env` must not reach the image. The
    port follows `COPY` and `ADD` through `.dockerignore` and ignores any later
    `RUN rm`, because a layer is immutable once written and `docker history`
    or a `docker save` will hand the file to anyone who pulls the image.
    Written positively too, for the counter-example that copies nothing: an
    image that holds no secret because it holds no app has not fixed anything.
    """
    path = context.params.text("path")
    expected = f"{path} is in the shipped image"
    if context.query.error() is not None:
        return CheckResult(passed=False, expected=expected, actual=NO_DEFINITION)
    present = context.query.path_in_image(path)
    return CheckResult(
        passed=present,
        expected=expected,
        actual=(
            f"{path} is copied into a layer of the image"
            if present
            else f"nothing copies {path} into the image"
        ),
    )


def _missing(context: ContainerContext) -> str:
    if context.query.error() is not None:
        return NO_DEFINITION
    return "<no such stage>" if context.query.stages() else "<the file has no FROM>"


def _no_process(context: ContainerContext) -> str:
    if context.query.error() is not None:
        return NO_DEFINITION
    return "<nothing sets a CMD or ENTRYPOINT>"
