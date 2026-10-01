# 0005 — Sandbox via a scoped directory and subprocess, not containers

- **Status:** accepted
- **Date:** 2026-10-01
- **Phase:** 3

## Context

[ADR 0003](0003-grade-git-exercises-by-repo-state.md) commits the project to
grading the end state of a real repository. That decision has a consequence this
one has to answer: something must build that repository and then execute the
learner's commands against it. Three properties are forced on whatever does.

**It must be reproducible across machines.** A commit hash covers the tree, both
parents, both identities, both timestamps and the message. Pinning the
identities and dates is necessary and not sufficient: `core.fileMode`,
`core.autocrlf` and `core.eol` differ between a Git for Windows install and a
Linux one, and `init.defaultBranch` falls back to `master` with a warning once
system and global config are excluded. If a fixture produces different hashes in
CI than on the author's machine, assertions written against it are untestable
and `content/fixtures.lock` is meaningless.

**It must not be able to damage anything that matters.** A learner practising
`git reset --hard` and `rm -rf` is going to run both. The blast radius has to be
a directory nobody cares about.

**It is not a security boundary, and pretending otherwise would be dishonest.**
All content is authored by the person running the tool, on their own machine, for
their own benefit. There is no adversary. Being precise about that distinction is
load-bearing for the rest of this record: a design justified as "secure" would
have to be held to a standard this one does not meet and does not need to.

Windows is the primary development machine and is in CI from Phase 0, so every
choice here has to work on both platforms rather than work on Linux and be
patched for Windows later.

## Decision

Run commands in a **scoped directory under the user cache, through
`subprocess` with an argv list**. No containers, no virtual machines, no
`chroot`, no seccomp.

Concretely:

- **Workspace** at `platformdirs.user_cache_dir("swe-practice")/ws/<short-id>`,
  where `short-id` is the first eight hex characters of the attempt id. The user
  cache rather than the system temp directory, so a failed attempt survives for
  inspection. Deliberately short, because Windows `MAX_PATH` is 260 characters.
  The repository is `<workspace>/repo`; the alias map, ref snapshot, clock,
  bare remotes and pinned gitconfig are its siblings, so none of them is visible
  to `git status`.
- **An environment built from nothing**, not inherited. `HOME` and `USERPROFILE`
  point at the workspace, `GIT_CONFIG_GLOBAL` at a workspace gitconfig,
  `GIT_CONFIG_NOSYSTEM=1`, `GIT_CEILING_DIRECTORIES` at the workspace, and
  `PATH` is rebuilt from the discovered git installation plus the platform's own
  directories. `os.environ` is never copied.
- **Pinned git config** written into that gitconfig on both platforms:
  `core.fileMode=false`, `core.autocrlf=false`, `core.eol=lf`,
  `core.longpaths=true`, `core.symlinks=false`, `init.defaultBranch=main`, a
  fixed `user.name`/`user.email`, no GPG signing, no colour, and
  `gc.auto=0` with reflog expiry disabled.
- **A trust split.** Fixtures are trusted code — you author them — and run under
  the bash bundled with git, with `--noprofile --norc`. Learner commands are
  untrusted input: `shlex.split` into an argv list, rejected if they contain
  `| < > & ; $( \``, checked against the exercise's own allowlist, and executed
  with `shell=False`. Nothing ever reassembles an argv into a string for a
  shell.
- **Virtual commands** (`write`, `append`, `rm`, `mkdir`, `cat`, `ls`, `pwd`)
  implemented in Python, because without a shell `echo x > file` cannot work and
  re-admitting shell parsing to get it back would undo the split above.
- **Limits:** a per-command timeout, 64 KB per output stream with a truncation
  marker, and a process-tree kill on timeout.
- **Explicit disposal**, plus a `practice gc` that at this phase only ever
  reports.

### The process-tree kill, because the obvious Windows answer is wrong

`subprocess.run(timeout=...)` kills the direct child only. A `git` that spawned
a helper leaves the helper running — which on Windows then holds file handles
and makes the workspace undeletable, turning one timed-out command into a
workspace that `practice gc` reports forever and can never collect.

- **POSIX:** `start_new_session=True` plus `os.killpg(os.getpgid(pid),
  SIGKILL)` reliably takes the whole group.
- **Windows:** `CREATE_NEW_PROCESS_GROUP` does **not** help. It exists so you
  can send `CTRL_BREAK_EVENT`; `Popen.kill()` still terminates only the direct
  child. Killing a tree requires assigning the child to a **Job Object** with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, or shelling out to `taskkill /T /F
  /PID`. The Job Object is the correct answer. **`taskkill` is what v1 does**,
  as the pragmatic one, and the known gap is recorded below.

## Consequences

**What this buys.**

- Hashes reproduce. `content/fixtures.lock` holds every fixture's commit aliases
  and refs, both CI jobs regenerate and compare, and a divergence names which
  platform diverged instead of merely going red.
- Zero infrastructure. No daemon to install, no image to pull, no network. The
  tool works on a laptop with no internet, which is one of the project's
  non-goals-inverted: offline is a feature, not a limitation.
- Fast. A fixture runs in well under a second, so the content suite can afford
  to run every fixture on every invocation rather than behind a marker.
- The learner's real git config cannot change how an exercise behaves, which is
  the difference between "it works on my machine" being a joke and being a bug
  report nobody can reproduce.

**What it costs, and these are real.**

- **No resource isolation.** A command can fill the disk, allocate all
  available memory, or spawn until the process table is full. The timeout and
  the output caps are the only limits. A container would give cgroups; this
  gives a directory.
- **No filesystem isolation beyond the environment.** The guard against
  `write ../../.bashrc` is a path check in our own code, not a kernel boundary.
  A learner who genuinely wanted to escape would only have to ask an *allowed*
  program to do it for them — `git` can write anywhere it is pointed. This is
  acceptable only because of the "no adversary" paragraph in the context, and it
  stops being acceptable the moment this runs content somebody else wrote.
- **A known gap on Windows.** `taskkill /T /F` is a best-effort tree kill, not a
  guaranteed one. A grandchild created in the window between the kill and the
  reap can survive, and if it holds a handle the workspace cannot be deleted —
  which `practice gc` will then report and be unable to collect. Low risk for
  single-function katas and a repository of three commits, and the honest fix is
  the Job Object.
- **Git Bash is a hard dependency on Windows**, and it has to be the *bundled*
  one. `shutil.which("bash")` finds `C:\Windows\System32\bash.exe` — WSL —
  which runs in a different filesystem and cannot see the workspace at all. So
  bash is located by walking up from the resolved `git` executable, which is
  more code than a `which` call and the only thing that works.
- **Determinism is tied to git's default object format.** A future default of
  SHA-256 changes every hash at once. That is why the lock file beats a literal
  in a test: the change shows up as a reviewable diff across every exercise
  rather than as a mystery red build.

## Alternatives considered

**Docker, or any container runtime.** The closest to winning, and rejected on
two grounds rather than one. The decisive one is that it makes the tool depend
on a daemon the user has to install, configure and keep running — for a local,
offline practice environment, that is a larger imposition than the whole rest of
the project. The second is that it would not even solve the hard problem: commit
hashes still depend on `core.fileMode` and the pinned identities, so the entire
environment-pinning apparatus above would still have to exist, just inside a
container. We would pay the full cost and keep the full complexity. It remains
the right answer if this ever runs untrusted content.

**The system temp directory instead of the user cache.** Simpler, and loses the
property that a failed attempt survives for inspection — some platforms sweep
the temp directory out from under a running process. Debugging a fixture is a
large part of authoring content, so "the evidence is still there" is worth more
than one less path to compute.

**A real shell for user commands, with a sanitiser.** Would give redirection and
pipes for free, which is genuinely attractive — `git log | head` is a thing
people type. Rejected because a sanitiser is a blocklist, and a blocklist for a
shell grammar is a thing that is wrong in a way you discover later. The argv
list plus a handful of virtual commands is a smaller surface that is *obviously*
right, and the cost is a short list of commands nobody can type.

**`chroot`, seccomp, or a Linux user namespace.** Real isolation, and not
portable. Windows is the primary development machine; a design whose safety
story only exists on one of the two supported platforms is not a design, it is a
preference.

**A pure-Python git implementation (dulwich, pygit2).** Would make fixtures
deterministic by construction and remove the subprocess problem outright.
Rejected because it defeats the purpose: the project teaches operational
competence with *git*, and grading a learner's `git reflog` against a
reimplementation of the reflog would be grading them against our bugs. Learners
must run the real binary, with its real messages and its real edge cases.

**Hard-coding expected commit hashes in a test** rather than a lock file.
Rejected because the failure is uninformative. A test asserting `c1 ==
"906e5c9"` goes red identically whether someone edited the fixture, the pinned
environment broke, or git changed its hashing — and all three need different
responses. A lock file separates them: one exercise moving is an edit, one
platform disagreeing is a broken environment, everything moving at once is a
format change.

## Revisit if

- The tool ever runs content authored by somebody other than the person running
  it — a shared exercise library, a classroom deployment, anything downloaded.
  Then the "no adversary" premise is false, every cost above becomes a
  vulnerability, and containers become the answer.
- The Windows tree-kill gap produces an uncollectable workspace in practice.
  Then implement the Job Object rather than adding retries around `taskkill`.
- Katas grow beyond single functions into anything that spawns processes or
  needs a memory limit, at which point resource isolation stops being optional.
- Git's default object format changes, which does not reverse this decision but
  does require regenerating the lock file as a deliberate, reviewed act.
