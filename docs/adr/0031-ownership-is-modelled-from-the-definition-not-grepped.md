# 0031 — Who owns a path is modelled from the definition, not grepped for

- **Status:** accepted
- **Date:** 2026-10-17
- **Phase:** 24

## Context

*Permission denied as non-root* is the most common thing that goes wrong the
day a service stops running as root, and Phase 23 planned it and did not
write it. Its reason is ADR 0030's last revisit item: every assertion that
could grade the fix read the text, and **measured on BuildKit, the text is
not where the answer is.**

- `WORKDIR /app/data` *after* `USER app` creates the directory owned by
  `app`. A check for `chown` before `USER` fails that correct answer.
- `COPY --chown=app:app . .` into the `/app` a root `WORKDIR` made gives
  `app` every file and not `/app`. An app that creates `/app/data` at start-up
  dies with `PermissionError`. A check for `--chown` passes that wrong answer.
- `RUN chown app /app/data` *after* `USER app` is `Operation not permitted`
  and the build stops. A check for `chown` passes it too.

What decides each of these is who owns each directory on the way to the path,
with what mode, and which uid and groups the container runs with. Docker
computes all of it from the definition before it starts a process, which is
ADR 0030's premise, so it can be computed here too. The question was whether
it could be computed **honestly**: without failing an answer that works, and
without passing one that does not, across the spellings a solver might use.

## Decision

**The layer model tracks ownership, and one assertion reads it.**

- Two port methods on `BuildQuery`. `account(user=None)` is what a `USER`
  value runs as: a uid and every gid the kernel checks, or `None` for a name
  `docker run` would refuse. `path_access(path)` is the owner and mode of
  every directory from `/` down to the path, or to its deepest ancestor when
  it does not exist, plus notes about lines the reader could not follow, and
  the first command that would stop the build. Both are answered from
  **numbers**, because the kernel compares numbers: `useradd -u 10001 app`,
  `chown 10001` and `USER app` are one owner.
- `adapters/container/filesystem.py` builds both by walking the stages:
  `WORKDIR`, `COPY` and `ADD` with `--chown`, `--chmod` and `--from`, and in
  a `RUN`, the `mkdir`, `install -d`, `chown`, `chgrp`, `chmod`, `rm`,
  `useradd`, `adduser`, `groupadd`, `addgroup` and `usermod` it runs
  directly. It keeps `/etc/passwd` and `/etc/group` as Debian's allocators
  would, starting from `python:3.12-slim`'s measured accounts.
- `domain/containers/ownership.py` holds the kernel's rule (`may`) and
  `path_writable {path, by?}`. The adapter uses the same `may` to decide
  whether a `mkdir` run as `app` would stop the build. A rule written twice
  would have drifted.
- A command the build would refuse is not applied: it sets `stopped`, and
  `path_writable` fails with the reason, because a build that stops ships no
  image. A command the reader cannot evaluate (`chown $(id -u app)`, `chmod
  g=u`) is not applied either, and becomes a note the failing verdict quotes.
  The solver is told when the grader is the limit.

## Consequences

**Every rule was measured, and four of them are not what the documentation
says.** `WORKDIR` and `COPY --chown` both create *missing* parents owned by the
user and leave existing ones alone. `COPY --from` keeps the source's owner
where `COPY` from the context ignores `USER`. `--chmod` applies to created
directories under the 022 umask. And `WORKDIR` under a bare uid makes it
`4242:4242`, where the same `USER 4242` *runs* with group 0. Each is a case
in `tests/integration/container/test_filesystem.py`. The uid allocators were
measured the same way, and they differ by tool: `useradd` takes one past the
highest id, `adduser` the first free one.

**Nine answers the prompt leaves open pass, and each was run.** Among them
the three a text check would fail (`WORKDIR` after `USER`, `USER` before
`WORKDIR`, `COPY --chown` into a directory `COPY` creates), a numeric user,
an arbitrary uid through group 0, and a `VOLUME`. The honesty tier builds
each on a real daemon and stores an upload through it.

**The cost is a thousand-line adapter that imitates three programs**:
BuildKit, coreutils and Debian's account tools. It reads what an answer to
this exercise plausibly contains and no further, and the line it draws is
written down: what a script does is invisible, and every base image is
assumed to have `python:3.12-slim`'s accounts. That holds for every exercise
in the library and would be false for `alpine`'s `adduser`, whose allocator
was not measured.

**One assertion behind two port methods is more port than §13 likes.** It
has its second implementation (the fake) and a conformance case, which is
what §13 asks. It does not have a second exercise, and that is the stated
risk.

## Alternatives considered

**Grade the text after all**: `instruction_matches` for `chown` before
`USER`, negated `instruction_matches` for `chmod 777`. The cheapest, and
measured to be wrong in both directions on answers a solver would really
write. ADR 0003 rejected this for git, and this exercise is the clearest
case of why.

**Read ownership off a built image.** `docker run --rm img stat` is the truth
and is ADR 0030's rejected live grading, for its reasons: no daemon in CI on
Windows, no network, and a minute per verdict on save. It is the honesty tier,
which is where each rule here was taken from.

**Write it up and not ship the exercise.** The brief allowed it, and it would
have been right if ownership could not be modelled without guessing. It
could. Every rule needed was measurable, and the one place a guess would have
been needed, an unreadable command, is a sentence in the verdict instead.

**Model names rather than numbers.** It would have been half the size and
failed `USER 10001` after `useradd -u 10001 app`, which is the answer
Kubernetes' `runAsNonRoot` pushes people towards, because it can check only
a numeric `USER`.

**Ask about `chmod 777` with a separate `mode_at_most` assertion.** The
advisory is `path_writable {by: nobody}` negated instead, which says what
the lesson is (not every account) and passes a group-writable answer that
a mode ceiling would have had to special-case.

## Revisit if

- **A second exercise grades ownership on a base that is not Debian's**
  (`alpine`, `node`, a distroless `:nonroot`). The accounts need to come from
  a small manifest of measured bases, the way ADR 0030's revisit list already
  says a base's `ENTRYPOINT` would.
- **A solver's correct answer is reported as a note** (*the grader cannot
  read ...*). The note is the grader admitting a limit. If it is reached by
  answers people really write, the command belongs in the walk.
- **Nothing but this exercise ever names `path_writable`** by the time the
  Docker track next grows. Then the two port methods are carrying one
  exercise and should be argued for again, not left by default.
