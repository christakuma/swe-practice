# 0030 — Docker exercises are graded on the definition, one editable file each

- **Status:** accepted
- **Date:** 2026-10-17
- **Phase:** 22

## Context

A user asked to practise DevOps: dockerising an app, and diagnosing a container
from its symptoms. PLAN.md had turned Docker down three times (§2, §11's
stretch menu, and ADR 0019's list of alternatives), each time for the same
reason: **a real container cannot be built or run offline on both CI
platforms.** Windows runners cannot run Linux containers, base images have to
be pulled over a network, and §2 forbids the network.

That reason rules out *running Docker in the grade*. It does not rule out
Docker *exercises*. The project's core bet is to grade the end state rather
than the answer text (ADR 0003), and for a Dockerfile or a compose file the
end state that can be read without a daemon is the **definition**: the image it
would be built from, the order of its layers, the process PID 1 would be, the
files its layers would hold, and the settings a compose service resolves to.
Docker computes every one of those from the files before it builds anything.

ADR 0019 also left a prediction for this phase: *"if the fourth kind is also
file-based, it is one clause [in `editable_source`]"*.

## Decision

**A fourth exercise kind, `container`, graded statically through a new
read-only port, with exactly one editable file per exercise.**

- `ContainerSpec`: a `context` directory copied into the workspace whole, a
  stub named exactly `Dockerfile` or `compose.yaml` so that `docker build .`
  and `docker compose up` work in the workspace unchanged, a reference, checks
  and counter-examples.
- `BuildQuery` in `domain/ports.py`, with `Stage` and `Instruction` as its
  vocabulary. It answers questions about what Docker *does* with the
  definition, not about the text: `effective_process` composes `ENTRYPOINT`
  and `CMD`, `path_in_image` applies `.dockerignore` and follows `COPY
  --from`, and `service` returns compose's long form whichever spelling the
  file used. Two implementations: `ParsedBuildQuery` and `FakeBuildQuery`.
- `domain/containers/`: a third assertion vocabulary, disjoint from the git and
  drill ones by construction (ADR 0019's argument). **Eight assertions**, each
  named by a shipped exercise.
- `adapters/container/`: a small Dockerfile parser, Docker's `.dockerignore`
  rules, a compose normaliser over PyYAML, the query and the grader. **No
  process is started anywhere in it.**
- **An opt-in honesty tier**, `tests/docker/`, skipped unless
  `PRACTICE_DOCKER_TESTS=1`. It builds every stub, reference and
  counter-example on a real daemon and asserts each ticket's symptom: the
  ten-second stop, the empty reply, the key in a layer, the API that loses the
  race. It never runs in CI and the grade never depends on it.

## Consequences

**ADR 0019's prediction held.** The new kind is one clause in
`editable_source`. Adding it to the `ExerciseSpec` union made mypy name exactly
one other site, the provisioner's `else`, which is a different question
(*what to copy in*) and was always going to need a branch. The workbench, the
solution-file handoff, `practice solve`, the tutor export and the MCP server
took the new kind without an edit.

**The vendored assets surprised for the second time.** ADR 0019 found that
`workbench.html` hard-coded the Python mode. This time the CodeMirror
Dockerfile mode is built on the `simple` mode addon, so a mode is now
*files*, in load order, and `vendor.mode_file` became `mode_files`.

**Writing the wrong answers found four places where the model would have failed
a correct one.** That is the one failure a grader must not have, because a
solver cannot tell *my answer is wrong* from *the grader is wrong*. Each was
found by writing out an answer a prompt does not rule out (CLAUDE.md's rule),
and each is now a measured case in `tests/integration/container/`:

1. `CMD exec python worker.py` makes python PID 1, because the shell
   replaces itself. The first model said `/bin/sh`.
2. `bash -c 'a && python w.py'` ends with python as PID 1. Bash execs the
   last command of an `&&` list without being asked.
3. A builder stage that copies `.env` and deletes it, then `COPY --from`
   into a clean final stage, ships no key, because `--from` copies the
   builder's *filesystem*, not its layers. The model now keeps two sets per
   stage, `layers` (what ships, which only grows) and `visible` (what `--from`
   reads, which `RUN rm` shrinks).
4. A `CMD` set *before* an `ENTRYPOINT` in the same stage survives it.
   BuildKit resets only an inherited `CMD`. This one was found by a test whose
   name said one thing and whose assertion said another.

**Every claim about Docker's behaviour was measured, and one piece of folklore
was wrong.** The plan doubted whether exercise 3's stub would reproduce at all:
the common advice is that a shell "execs the last command". Measured on
`python:3.12-slim`, `/bin/sh` is **dash 0.5.12, and dash does not**: PID 1
stays `/bin/sh -c python worker.py`, and python is PID 7. Bash 5.2 in the
same image does exec. The postgres image's first-boot server listens on the
Unix socket only (`listen_addresses=''`, line 297 of its entrypoint), which
is why the reference healthcheck uses `-h 127.0.0.1`. Every ticket in the
library is real captured output.

**What static grading cannot see**, stated so nobody assumes otherwise:

- A base image's own `ENTRYPOINT` or `USER`. An image built `FROM` something
  outside the file is assumed to set neither, which holds for the `python`
  images every exercise uses and is false for `node`.
- Anything a `RUN` does beyond `rm`. A file a script deletes is still visible
  to `COPY --from`. That is the conservative direction for a secrets check,
  since it reports a leak rather than missing one.
- Whether the app works. A Dockerfile can satisfy every check and copy a
  broken `app.py`. The honesty tier is the only thing that runs one.

**The cost is a parser this project now owns.** It is about 350 lines and
covers what an assertion reads. It refuses heredocs and unknown instructions
with a sentence and a line number, through the synthesised
`definition-parsed` check, rather than half-reading them.

## Alternatives considered

**Grade with a real daemon** (build, run, probe). The most realistic option, and
the one PLAN.md had already refused three times for a reason that has not
changed: it cannot run in CI on Windows, it needs the network for base
images, and a verdict that takes a minute to build an image is wrong for
grade-on-save (ADR 0013). It survives as the honesty tier, where the cost is
paid once per exercise change rather than once per keystroke.

**Static grading plus a live advisory tier when a daemon is present.** It was
offered to the user and declined in favour of static only. It would have made
a verdict depend on what was installed on the machine grading it, which no
other kind does.

**Lint with hadolint.** It is a Haskell binary, which cannot be vendored the way
CodeMirror is. It checks style rules rather than end states (it cannot say what
PID 1 will be), and its rules are not this library's lessons.

**Grade the text of the Dockerfile.** Rejected by ADR 0003, and worth restating
because it is so tempting here: "does it contain `CMD [`?" passes
`CMD ["sh", "-c", "python w.py"]`, which is the exact bug, and fails
`CMD exec python w.py`, which is a fix.

**Several editable files per exercise.** A `.dockerignore` *and* a
Dockerfile, or an entrypoint script and a Dockerfile, would be closer to some
real fixes. But one source per attempt runs through `SolutionSaved`, own-editor
mode, the CodeMirror pane, `practice solve` and the tutor export, and every one
of the six exercises can be fixed in one file. The notes cover `.dockerignore`.

**Ten assertions, as planned.** `stage_count` and `service_mount` were cut:
no exercise in the first batch is multi-stage or mounts a volume, and §13's
rule is that an assertion arrives with the exercise that wants it.

## Revisit if

- **An exercise needs two editable files.** That is the trigger for the
  per-kind capability record ADR 0019 anticipated, and it is a change to
  `SolutionSaved` and the workbench, not to this kind.
- **An exercise is built on an image with its own `ENTRYPOINT`** (`node`,
  `nginx`). The query would need the base's config handed to it, a small
  manifest of known bases, rather than the current assumption.
- **CI gains a Linux job with a Docker daemon.** The honesty tier could then
  run there on every content change, which would turn "every ticket is real"
  from a claim checked by hand into one checked by the build.
- **The multi-stage or volume exercises are written.** `stage_count` and
  `service_mount` come back with them.
