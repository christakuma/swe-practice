# swe-practice — Implementation Plan

An offline practice environment for the two things entry-level engineers are
actually tested on: **data-structure problem solving** and **operational
competence with git**. Local web app, no network, no accounts, no CDN.

> **Status:** Phase 6 complete — **the core bet works, and an attempt survives
> the process that started it.** A git scenario is graded end to end: `practice
> solve git/revert-a-pushed-commit --reference` passes, and the same exercise
> replayed with `reset --hard` fails `history-preserved` while passing
> `content-restored`, because the trees are identical and the ancestry is not. Two
> `RepoQuery` implementations proved to agree, 22 pure assertions, a scenario
> grader, and a content suite that grades every reference solution and holds every
> counter-example to the checks it declares. On top of that, an attempt now lives
> in SQLite: `start`, `resume`, `resume`, `submit` is four processes sharing one
> repository, one event log and one budget, and `practice gc` can finally say
> which workspace is an orphan.
> **Owner:** Chris Sweet · **Plan written:** 2026-09-30

---

## 1. Product thesis

Most practice tools grade *recognition*. You read "how do I undo a pushed
commit?", you flip the card, you nod, you learn nothing. Recognition is not the
skill. The skill is being dropped into a repo that is already broken and knowing
what to look at first.

So the core bet of this project is:

> **Grade the end state, not the answer text.**

A git exercise ships a **fixture** that builds a real repo in a throwaway
directory with a real problem in it — detached HEAD, a bad merge, a commit
pushed to a shared branch, a stash you forgot about. You then run real git
commands against it. Grading inspects the **resulting repo state** and reports
against declarative assertions.

That single decision buys a lot:

- `git revert`, `git reset --hard`, and `git checkout <sha> -- .` are all judged
  on what they actually did, **including how they differ**.
- Feedback can be nuanced instead of binary: *"Correct tree, but you rewrote
  history that was already published — here's why that's the wrong tool here."*
- No string matching, so the tool never punishes a correct answer it didn't
  anticipate.
- The fixture **is** the lesson. Reading a broken repo is the thing being taught.

Code katas get the same treatment, just with an easier oracle: run the hidden
test suite.

### Non-goals (v1)

Deliberately out of scope, so the first release actually ships:

| Not doing | Why |
|---|---|
| Accounts, sync, multiplayer | Single-user local tool. Nothing to sync. |
| Redistributing LeetCode problem text | Copyrighted. We write our own prompts and reference problems by number only. |
| Docker-based sandboxing | Temp dirs are sufficient when you author all the content. Kept as a future adapter. |
| An embedded terminal (xterm.js/pty) | Structured command input is what makes grading and replay possible. Revisit after the model is proven. |
| SQL / system design / k8s drills | The architecture must make them *possible*. v1 ships two types done properly. |
| Mobile / responsive polish | Desktop-only tool used at a desk. |

A finished narrow tool beats an unfinished broad one, and "here's what I cut and
why" is a stronger interview answer than a feature list.

---

## 2. Stack

Decided. Rationale in the ADRs listed in §12.

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.13 | pytest is the natural kata oracle; strongest fit for the content tooling. |
| Packaging | `uv` | Fast, lockfile-based, one tool for venv + deps + scripts. |
| Web | FastAPI + `uvicorn` | Bound to `127.0.0.1` only. |
| Templating | Jinja2 + HTMX | No build step, no npm, all logic stays in Python. |
| Editor | CodeMirror 5 (vendored) | See §8.2 — CM5 ships single-file JS/CSS, CM6 needs a bundler. |
| Validation | Pydantic v2 | Content schema + API DTOs. |
| Content format | YAML via `PyYAML` | Hand-authored exercise files; see ADR 0004 for why not TOML. |
| Storage | SQLite via stdlib `sqlite3` | Hand-rolled migrations, explicit mappers, no ORM. |
| Lint / types | `ruff`, `mypy --strict` | Both gate CI. |
| Tests | `pytest`, `hypothesis` | Property tests on the scheduler. |
| File watching | `watchfiles` | For "solve it in my own editor" mode. |
| CLI | `typer` | A thin second adapter — see below. |

**Runtime dependencies must never include anything that phones home.** A test
enforces that no template or static asset references an external URL.

### Why a CLI *and* a web app

The web UI is the real interface — commit graphs, diffs, and syntax-highlighted
code are genuinely painful in a terminal. But a ~200-line Typer CLI gets built
alongside it as a **second adapter over the same use cases**.

That's not busywork. It is the proof that the hexagonal boundary is real and not
decorative: if the core were secretly coupled to HTTP, a second driving adapter
wouldn't work. It also makes end-to-end tests trivial to write and keeps
`practice validate` runnable in CI without booting a server.

---

## 3. Architecture

Ports and adapters (hexagonal). Dependencies point **inward**.

```
                     ┌──────────────────────────────────────────┐
                     │              interface/                  │
                     │   web (FastAPI + Jinja + HTMX)           │
                     │   cli (Typer)                            │
                     └────────────────┬─────────────────────────┘
                                      │ invokes use cases
                     ┌────────────────▼─────────────────────────┐
                     │             application/                 │
                     │   StartAttempt   SubmitSolution          │
                     │   RunScenarioCommand   GradeReview  ...  │
                     │   DTOs · exercise-kind registry          │
                     └────────────────┬─────────────────────────┘
                                      │ depends only on ports
                     ┌────────────────▼─────────────────────────┐
                     │               domain/                    │
                     │   Exercise  Attempt  Verdict  ReviewCard │
                     │   CheckSpec  Sm2Scheduler                │
                     │   ports.py ◄── Protocol definitions      │
                     └────────────────▲─────────────────────────┘
                                      │ implements
                     ┌────────────────┴─────────────────────────┐
                     │              adapters/                   │
                     │   content/filesystem  persistence/sqlite │
                     │   sandbox/subprocess   git/*   kata/*    │
                     │   clock · ids                            │
                     └──────────────────────────────────────────┘

        composition.py — the ONLY module that imports across all layers
```

Three properties worth defending in an interview:

1. **The domain has zero I/O.** No `subprocess`, no `sqlite3`, no filesystem
   writes, no HTTP. It is pure data and pure functions, so its tests run in
   milliseconds and never touch a disk.
2. **`composition.py` is the single wiring point.** Manual dependency injection,
   no framework, no magic. You can read the entire object graph in one file.
3. **The boundary is enforced by a test, not by discipline.**
   `tests/unit/test_architecture.py` walks the AST of every module under
   `domain/` and `application/` and fails the build if any of them imports from
   `adapters/` or `interface/`. Architecture that isn't tested decays.

That last one is cheap to write and does more to demonstrate architectural
seriousness than any amount of prose.

---

## 4. Domain model

### 4.1 Value objects

```python
# domain/ids.py — identifiers and scalars
ExerciseId   # exactly "<track>/<slug>", e.g. "git/revert-a-pushed-commit"
AttemptId    # uuid4; .short is the 8 hex chars the workspace dir uses (§8.1)
Sha          # git object hash, normalised to lowercase
Tag          # NewType(str) + a tag() validator: "two-pointers", ...

# each enum sits with the concept it describes, as a StrEnum whose values are
# the ones in exercise.yaml — so the loader gets Difficulty("medium") for free
ExerciseKind = "kata" | "git_scenario"                    # exercise.py
Difficulty   = "intro" | "easy" | "medium" | "hard"       # exercise.py
Severity     = "required" | "advisory"                    # verdict.py
Outcome      = "pass" | "pass_with_advisories" | "fail"   # verdict.py
Grade        = "again" | "hard" | "good" | "easy"         # review.py
CardState    = "new" | "learning" | "review" | "lapsed"   # review.py
```

Every one validates on construction, so an invalid identifier cannot exist
anywhere downstream. `InvalidValueError` subclasses **both** `DomainError` and
`ValueError`, which is load-bearing rather than taxonomy: the Phase 2 Pydantic
schema builds these value objects inside field validators, and Pydantic turns a
`ValueError` raised there into a validation error with the field path attached.
Without it, every invariant in the domain would have to be restated in the schema
layer to get a readable message, and the two copies would drift.

`ExerciseId` is exactly two segments because the id **is** the content path. A
loader that derives ids from directories and a type that accepts any depth
disagree the first time someone nests a directory.

### 4.2 `Exercise` — content aggregate (immutable)

Common metadata plus a discriminated `spec` union. **Composition, not
inheritance** — a flat union keeps the kind-registry pattern clean and avoids a
class hierarchy that needs re-cutting the moment a third kind arrives.

```python
@dataclass(frozen=True)
class Exercise:
    id: ExerciseId
    kind: ExerciseKind
    title: str
    prompt: str                 # markdown
    difficulty: Difficulty
    tags: tuple[Tag, ...]
    estimated_minutes: int
    hints: tuple[Hint, ...]     # ordered, progressive
    notes: str                  # revealed after grading
    spec: KataSpec | GitScenarioSpec
```

### 4.3 `Attempt` — session aggregate (mutable, invariant-enforcing)

```python
@dataclass(frozen=True)
class AttemptPolicy:
    """Limits copied from the Exercise when the Attempt is constructed."""
    max_commands: int
    hints: tuple[Hint, ...]
    allowed_commands: frozenset[str]

class Attempt:
    id: AttemptId
    exercise_id: ExerciseId
    policy: AttemptPolicy
    started_at: datetime
    finished_at: datetime | None
    status: AttemptStatus           # ACTIVE | COMPLETED | ABANDONED
    events: list[AttemptEvent]      # CommandRun | HintRevealed | SolutionSaved
    hints_revealed: int
    declared_complexity: ComplexityClaim | None   # time and space, katas only
    verdict: Verdict | None

    def record_command(self, argv, result, *, at) -> CommandRun: ...
    def reveal_next_hint(self, *, at) -> Hint: ...
    def save_solution(self, source, *, at) -> None: ...
    def declare_complexity(self, claim) -> None: ...
    def complete(self, verdict, *, at) -> None: ...
    def abandon(self, *, at) -> None: ...
    def elapsed(self, now) -> timedelta: ...
```

Invariants it enforces (each with a unit test): cannot record events after
completion **or abandonment**; cannot complete twice; cannot reveal more hints
than the policy holds; command count cannot exceed `policy.max_commands`;
`argv[0]` must be in `policy.allowed_commands`; every timestamp is
timezone-aware and never earlier than the last event.

Timestamps are arguments, not readings, because the domain has no clock — the
`Clock` port is injected into the use case that drives the aggregate. Naive
datetimes are rejected rather than normalised: guessing a zone is how an attempt
ends up with a duration of minus seven hours.

`declared_complexity` holds **both** axes rather than one string, because the
`ComplexityExpectation` it is compared against has two and one string cannot
disagree with an expectation on only one of them. `AttemptStatus` is here because
§8.1 defines the lifecycle as active until submitted *or abandoned*, and the
workspace lifetime and `practice gc`'s definition of an orphan both hang off that
flag.

The allowlist is checked here **and** in the Phase 3 sandbox command policy.
Deliberate duplication with different jobs: the adapter refuses to *execute* a
disallowed command, the aggregate refuses to *remember* one, so a future
execution path that forgets the check cannot produce an attempt whose log
contradicts the exercise's own rules.

**`AttemptPolicy` is not incidental.** The aggregate holds an `ExerciseId`, not
an `Exercise` — so without the policy copied in at construction it cannot
enforce a single one of the rules above, and every limit check leaks out into
the use cases where it will eventually be forgotten on one code path. Copying
the limits in keeps enforcement where the invariant lives.

Keeping the **full event log** rather than just a final state is what makes
replay, "where did I go wrong" feedback, and the advisory checks in §6.3
possible. It costs almost nothing and unlocks a lot.

### 4.4 `Verdict` and `CheckReport`

```python
@dataclass(frozen=True)
class CheckReport:
    check_id: str
    label: str                 # human sentence, written by the content author
    severity: Severity
    passed: bool
    expected: str | None
    actual: str | None
    explanation: str | None    # why this matters, shown on failure

@dataclass(frozen=True)
class Verdict:
    reports: tuple[CheckReport, ...]
    @property
    def outcome(self) -> Outcome: ...     # pure derivation
```

`ADVISORY` severity is the feature that makes the tool worth using. A verdict of
`PASS_WITH_ADVISORIES` means *you achieved the goal, but the way you did it has
consequences* — force-pushing a shared branch, reaching for `reset --hard` when
`revert` was called for, brute-forcing an O(n) problem in O(n²). That is exactly
the feedback a code reviewer gives and a flashcard cannot.

### 4.5 `ReviewCard` — scheduling aggregate

```python
@dataclass(frozen=True)
class ReviewCard:
    exercise_id: ExerciseId
    state: CardState       # NEW | LEARNING | REVIEW | LAPSED
    ease: float            # >= 1.3
    interval_days: int
    reps: int
    lapses: int
    due_on: date
    last_reviewed_at: datetime | None
```

### 4.6 Ports (`domain/ports.py`) — all `typing.Protocol`

| Port | Responsibility |
|---|---|
| `ContentRepository` | `list_exercises(criteria)`, `get(exercise_id)` |
| `AttemptRepository` | `save`, `get`, `history_for(exercise_id)` |
| `ReviewRepository` | `get_card`, `save_card`, `due_on(date)` |
| `SandboxProvisioner` | `provision(exercise, attempt_id) -> Workspace`, `attach` to resume |
| `Workspace` | `run(argv, timeout)`, `run_tool(argv, timeout)`, `read_file`, `write_file`, `dispose` |
| `RepoQuery` | read-only git interrogation — see §6.2 |
| `Grader` | `grade(exercise, workspace, attempt) -> Verdict` |
| `Scheduler` | `next_card(card, grade, today) -> ReviewCard` |
| `Clock` | `now()`, `today()` |
| `IdGenerator` | `new_attempt_id()` |

`Clock` and `IdGenerator` look like over-engineering until the first test that
needs a deterministic due date or a stable snapshot. Inject them from day one;
retrofitting them is miserable.

**`Workspace.run_tool` is the trust split of §8.1, named on the port.** `run` is
untrusted input — whatever the solver typed, under the exercise's allowlist.
`run_tool` is trusted code: an argv a grading engine built for itself, which no
allowlist could usefully gate because the exercise author never wrote it down. A
kata's allowlist is *empty* by design, so the kata engine's own
`python -m pytest` has no other way in; putting it on the port rather than
reaching for the concrete workspace is what keeps `Grader` implementable against
the protocol (§16, Phase 4).

---

## 5. Content as data

**The highest-leverage decision in the project.** Adding fifty git scenarios must
require zero code changes and zero recompiles. If authoring content means
touching Python, the content library stops at eight exercises and the tool dies.

```
content/
  katas/
    two-sum/
      exercise.yaml        # metadata, prompt, hints, kata spec
      stub.py              # what you start from
      tests.py             # hidden until graded
      solution.py          # reference — CI asserts it passes
      notes.md             # revealed after grading
  git/
    revert-a-pushed-commit/
      exercise.yaml
      fixture.sh           # builds the broken repo (trusted bash)
      solution.cmds        # reference — CI asserts it passes
      naive.cmds           # a plausible WRONG answer — CI asserts it fails
      notes.md
```

### 5.1 Kata file

```yaml
schema_version: 1
id: katas/two-sum
kind: kata
title: Two Sum
difficulty: easy
tags: [arrays, hash-map]
estimated_minutes: 15
prompt: |
  Given an array of integers and a target, return the indices of the two
  numbers that add up to the target. Exactly one solution exists; you may
  not use the same element twice.
hints:
  - "What would change if the array were sorted?"
  - "You are allowed to trade space for time."
  - "A dict of value -> index lets you check the complement in O(1)."
kata:
  language: python
  stub: stub.py
  tests: tests.py
  reference: solution.py
  time_limit_seconds: 10
  complexity:
    expected_time: "O(n)"
    expected_space: "O(n)"
```

There is deliberately **no `references:` field**. The first draft had
`references: {leetcode: 1}` as a pointer to the problem's origin, and nothing
consumes it: the schema forbids unknown keys, so a field that is accepted and
then dropped is worse than one that does not exist yet. Attribution lives in
prose in `notes.md` until a page actually displays it (§13's rule about
abstractions earning their keep, applied to data).

### 5.2 Git scenario file

```yaml
schema_version: 1
id: git/revert-a-pushed-commit
kind: git_scenario
title: Undo a commit that is already on origin
difficulty: medium
tags: [history, revert, collaboration]
estimated_minutes: 10
prompt: |
  You pushed `c3` to origin/main an hour ago. A teammate has already pulled
  it. It broke the build. Get main working again without rewriting history
  that other people already have.
scenario:
  fixture: fixture.sh
  reference: solution.cmds
  # Shown here as it was first drafted. §5.4 supersedes it: the long form
  # with `expect_failures:` is the only one the schema accepts.
  counter_examples: [naive.cmds]
  allowed_commands: [git, ls, cat, write, append, rm, mkdir, pwd]
  max_commands: 25
  checks:
    - id: tree-matches-c2
      label: The committed tree matches the state before the bad commit
      severity: required
      assert: tree_equals
      with: {ref: HEAD, target: "@c2"}
      explanation: |
        HEAD should point at a commit whose tree is identical to c2's. This is
        about committed content, not your working directory — clean-tree below
        covers that separately. Whether you got here by reverting or resetting
        is the next question.

    - id: clean-tree
      label: Nothing left uncommitted
      severity: required
      assert: worktree_clean

    - id: history-preserved
      label: c3 is still reachable — you did not rewrite published history
      severity: required
      assert: is_ancestor
      with: {ancestor: "@c3", descendant: HEAD}
      explanation: |
        Your teammate already has c3. If it is no longer an ancestor of main,
        their next pull will conflict or silently resurrect the bad commit.
        `git revert` adds a commit that undoes c3 while keeping it in history.

    - id: fix-published
      label: The fix is on origin, not just on your machine
      severity: required
      assert: ref_points_at
      with: {ref: "refs/remotes/origin/main", target: HEAD}
      explanation: |
        The build is broken for everyone. Until origin/main points at your
        fix, your teammate's next pull still gets the breakage.

    - id: no-force-push
      label: You did not force-update the shared branch
      severity: advisory
      assert: command_not_used
      with: {pattern: "push .*(-f|--force)"}
```

### 5.3 Reference solutions are command lists, not scripts

A subtle trap worth naming explicitly, because getting it wrong would have
quietly poisoned the whole content library.

Fixtures are **trusted bash** — you author them, they get a real shell. User
commands are **untrusted input** — no shell, argv only, allowlisted (§8.1).
If reference solutions were also bash scripts, they would be validated through
an execution path *you cannot use*: `solution.sh` could pipe and redirect while
you are forbidden from typing `|`. CI would then prove only "a solution exists",
not "a solution exists within the rules" — and a scenario could ship literally
unsolvable with the build still green.

So reference and counter-example solutions are **plain command lists**, replayed
through the real `RunScenarioCommand` against the real policy:

```
# solution.cmds — one command per line; blank lines and # comments ignored
git log --oneline
git revert --no-edit @c3
git log --oneline
```

Three things fall out of this for free:

- CI proves solvability **under the same constraints you face**.
- The list is directly replayable, so "show me how" becomes a UI feature with
  no extra machinery — step through the reference solution one command at a
  time and watch the repo state change.
- Counter-examples get the same guarantee, so `naive.cmds` is a fair test of
  whether the assertions actually discriminate.

### 5.4 Schema enforcement

Pydantic v2 models in `adapters/content/schema.py`, exercised by:

- `practice validate` — CLI command, runs in CI, validates every file on disk.
- A parametrized test over every exercise directory (see §9, item 5).
- A check that every `assert:` name exists in the check registry, so a typo in
  YAML is a build failure rather than a silently skipped assertion.
- **At least one `required` check per exercise.** Without this rule an exercise
  whose checks are all `advisory` passes vacuously, which is worse than having
  no exercise at all.
- Every command in `reference` and `counter_examples` must satisfy the
  exercise's own `allowed_commands` policy — caught at validation time, not at
  grading time.
- **Every counter-example declares which checks it must fail**, via
  `expect_failures: [check-id, ...]`:

  ```yaml
  counter_examples:
    - file: naive-reset-main.cmds
      expect_failures: [main-untouched]
  ```

  "Fails at least one check" is too weak a contract, and §6.6 showed why:
  counter-examples that reference `HEAD@{n}` depend on reflog indices that
  shift when a command is added. An edit could silently leave a
  counter-example failing for an unrelated reason — or passing outright —
  with CI none the wiser. Naming the expected failure makes that rot a build
  error. Other checks may also fail; the named ones must.

---

## 6. The git scenario engine

The most interesting subsystem, and the one most worth being able to talk
through.

### 6.1 Fixtures and determinism

A fixture is a **trusted** bash script (you author it) that builds the starting
repo inside a fresh workspace. Two mechanisms make fixtures reliable:

**Deterministic SHAs.** A commit hash covers the tree, the parents, both
identities, both timestamps, and the message. Pinning the identities and dates
is necessary but **not sufficient** — three more inputs silently differ between
Windows and Linux and will change the *tree* hash underneath you.

Environment (requires **git ≥ 2.32** for the `GIT_CONFIG_*` overrides):

```
GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL / GIT_AUTHOR_DATE
GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL / GIT_COMMITTER_DATE
GIT_CONFIG_GLOBAL  → <workspace>/.gitconfig
GIT_CONFIG_NOSYSTEM=1
```

Workspace git config, set explicitly on **both** platforms rather than left to
defaults:

| Setting | Why |
|---|---|
| `core.fileMode=false` | Git for Windows writes `false` at init, Linux writes `true`. One `chmod +x` in a fixture yields mode `100755` on Linux and `100644` on Windows — different tree, different commit SHA. |
| `core.autocrlf=false`, `core.eol=lf` | The defaults happen to be safe once system config is excluded, but a reproducibility guarantee must not rest on a default that an installer can change. |
| `init.defaultBranch=main` | With global and system config excluded, git falls back to `master` and warns. Without this, any fixture referring to `main` fails outright. |
| `core.longpaths=true` | See §8.1 — Windows `MAX_PATH`. |

With all of that pinned, identical content produces identical hashes on every
run and every machine. Note the hashes are still tied to git's **default object
format**; a future default of SHA-256 would change every SHA at once, which is
why the lock file below beats hard-coding a literal in a test.

**The clock must span the whole attempt, not just the fixture.** Found by
actually running this (§6.5): if the pinned dates only cover fixture commits,
any commit *the user* makes falls back to wall-clock time and the attempt stops
being reproducible. No assertion depends on a user commit's SHA — they compare
trees and ancestry — but reproducing a bug report, or storing a golden
end-state, needs the whole attempt to be deterministic. So the sandbox
continues the fixture's clock into the attempt, advancing it per command, which
also keeps `git log` ordering sensible instead of stacking every commit at one
instant.

**Symbolic aliases.** Even with deterministic hashes, hard-coding SHAs into
assertions is unreadable and breaks whenever a fixture is edited. A sourced
helper library gives fixtures a `commit_as` function:

```bash
source "$PRACTICE_FIXTURE_LIB"
commit_as c1 "add build script"
commit_as c2 "add parser"
commit_as c3 "refactor parser (this is the bad one)"
mkremote origin           # a local bare repo — no network, ever
push origin main
```

`commit_as` appends `c1=<sha>` to `$PRACTICE_ALIASES`. The check engine resolves
`@c2` through that map. Assertions read like English; fixtures stay editable.

**Ref snapshot.** After the fixture completes, the provisioner records every ref
and its SHA into `$PRACTICE_SNAPSHOT`. That is what makes
`ref_unchanged {since: fixture}` possible — the engine can tell whether
`origin/main` moved during your attempt.

### 6.2 `RepoQuery` — the read-only port

Checks must be **pure and unit-testable without git installed**. The move that
makes this work: checks never shell out. They depend on a narrow read-only port.

Because they are pure functions over a port, **the check functions live in
`domain/checks/`, not in `adapters/`** — only `GitRepoQuery` is an adapter. That
placement is not pedantry: it puts the most correctness-critical code in the
project inside the layer the coverage gate and the architecture test actually
police (§9), and it makes "testable without git" a structural fact rather than a
happy accident.

```python
class RepoQuery(Protocol):
    def rev_parse(self, rev: str) -> Sha | None: ...
    def tree_sha(self, rev: str) -> Sha | None: ...
    def is_ancestor(self, a: Sha, b: Sha) -> bool: ...
    def subject(self, rev: str) -> str | None: ...
    def refs(self) -> Mapping[str, Sha]: ...
    def status(self) -> WorktreeStatus: ...      # staged/unstaged/untracked/unmerged
    def reflog(self, ref: str) -> Sequence[ReflogEntry]: ...
    def log(self, rev: str) -> Sequence[CommitInfo]: ...
    def stash_list(self) -> Sequence[str]: ...
    def read_blob(self, rev: str, path: str) -> bytes | None: ...
    def aliases(self) -> Mapping[str, Sha]: ...
    def snapshot(self) -> Mapping[str, Sha]: ...
```

Two implementations:

- `GitRepoQuery` — real `git` subprocess calls using machine-readable formats
  (`status --porcelain=v2`, `log --format=%H%x00%T%x00%s`). Caches within a
  single grading pass.
- `FakeRepoQuery` — an in-memory DAG built from a small literal in the test.

Every one of the 22 assert types gets full unit coverage against the fake, in
milliseconds, with no filesystem. Integration tests then verify `GitRepoQuery`
agrees with real git on a handful of real repos. This is the difference between
a check engine you can refactor confidently and one you are afraid of.

### 6.3 The assertion vocabulary

Each `assert:` is a registered pure function
`(RepoQuery, params, Attempt) -> CheckReport`. v1 vocabulary:

**Negation is a modifier, not a separate assert.** Any check may carry
`not: true`, which inverts its result. The first draft of this section had
paired opposites — `branch_exists`/`branch_absent`,
`worktree_clean`/`worktree_dirty`, `command_used`/`command_not_used` — but
`head_detached` had no partner, and authoring the recovery scenario in §6.6
needed exactly that missing negation. Rather than add a sixth pair, the twins
are gone: one mechanism, no "does this one have a negative form?" guesswork,
and 27 asserts down to 22. The `label:` field carries the human sentence, so
nothing reads worse in practice.

**Refs and shape**
`ref_points_at` · `branch_exists` · `head_detached` · `is_ancestor` ·
`commit_count` (`equals`/`at_least`/`at_most`) · `commit_subject_matches` ·
`ref_unchanged {since: fixture}` · `linear_history` · `tag_exists` ·
`tag_points_at`

**Trees and content**
`tree_equals` · `file_exists` · `file_matches` · `file_at_ref_matches`

**Worktree and index**
`worktree_clean {include_untracked?}` · `index_staged {paths}` ·
`unmerged_paths_empty` · `no_conflict_markers`

**Recovery surfaces**
`stash_count` · `reflog_contains {ref, pattern}` †

**Process (advisory — reads the `Attempt` event log, not the repo)**
`command_used {pattern}` · `command_count {at_most}` †

† **Unproven.** Two exercises in and neither of these has found an honest use.
`reflog_contains` turns out to be either vacuously true (the fixture put the
entry there) or a way of grading *how* the user got somewhere, which is the
thing §1 exists to reject. `command_count` is worse than useless on the
recovery exercise: a "found it efficiently" budget counts read-only commands,
so it punishes precisely the inspection that the `used-the-reflog` advisory
rewards. It would need a `mutating_only: true` filter, which in turn needs a
maintained list of read-only git subcommands.

Both stay in the vocabulary for now, both are flagged, and per the §13 rule
about abstractions earning their keep: **if no exercise in Phase 11 needs
them, they get deleted rather than carried.**

**Phase 5 turned both flags into tests**, so the evidence survives to the review
rather than depending on someone remembering this paragraph.
`test_it_is_vacuously_true_where_the_fixture_made_the_entry` asserts that an
attempt which ran *no commands at all* passes `reflog_contains {pattern: "^reset:"}`
on the recovery exercise. `test_it_counts_read_only_commands_which_is_why_it_is_on_probation`
runs that exercise's own reference solution past a five-command budget: it fails,
while `used-the-reflog` passes on the same attempt. Two checks pulling in opposite
directions on one correct answer is the argument, and it is now in the suite.

The process assertions are why `Attempt` keeps a full event log. `command_used`
can reward reaching for the reflog on a "recover a lost commit" exercise;
`command_not_used` can flag a force-push that technically produced the right
tree. Correctness and craft, graded separately.

### 6.4 Grading flow

```
StartAttempt
  → provision workspace (scoped env, fresh dir)
  → run fixture.sh under Git Bash (trusted)
  → capture alias map + ref snapshot
  → return prompt + initial repo state

RunScenarioCommand  (repeated)
  → policy check: argv[0] in allowed_commands, no shell metacharacters
  → execute in workspace with timeout + output cap
  → append CommandRun to Attempt
  → re-render repo state panel

SubmitScenario
  → build GitRepoQuery over the workspace
  → evaluate every CheckSpec → CheckReport
  → assemble Verdict → derive Outcome
  → persist Attempt, suggest a review Grade, dispose workspace
```

### 6.5 Semantics the engine has to pin down

Details that look like implementation trivia but change whether assertions are
fair. Each was found by building the flagship scenario and running it (§6.6),
not by thinking about it.

**Revision resolution.** Every `ref:` and `target:` accepts, in this order:

1. `@alias` — a fixture alias, matched as `^@[A-Za-z][A-Za-z0-9_-]*$` and
   resolved from the alias map **before git ever sees the string**.
2. Anything git accepts — `HEAD`, `main`, `refs/remotes/origin/main`, `HEAD~1`.

Aliases are resolved first so they can never be confused with git's own `@`
syntax. Worth stating loudly in the authoring guide: **`@c2` is assertion
syntax only.** Content authors must not write it in `solution.cmds`, because
the user cannot type it — they only ever see real revisions.

**A missing ref is a clean failure, never an error.** If a check names
`refs/remotes/origin/main` and the user deleted the remote, the assertion must
report `passed: false` with `actual: "<ref does not exist>"`. A traceback in
the verdict panel teaches nothing, and half the point of these exercises is
that the repo may be in a state you did not anticipate.

**`worktree_clean` ignores untracked files by default.** No staged changes, no
unstaged changes, no unmerged paths — but a scratch file the user created while
poking around does not fail them. Exercises that genuinely care take
`worktree_clean {include_untracked: true}`.

### 6.6 Validated end to end before writing any code

`content/git/revert-a-pushed-commit/` is authored and was executed by hand
against real git before Phase 0 began — fixture, both counter-examples and all
six checks. The results:

| | content-restored | history-preserved | fix-published | advisories |
|---|---|---|---|---|
| `solution.cmds` (revert, push) | pass | pass | pass | both pass |
| `naive-reset-force.cmds` | **pass** | **fail** | pass | force-push flagged |
| `naive-forgot-push.cmds` | **pass** | pass | **fail** | both pass |

The first column is the whole argument for §1 in one line: **content-restored
passes for all three.** The trees are byte-identical — `0b2626fa` in every
case. Any tool grading on file content alone accepts both wrong answers, and a
tool matching command text would have to guess which of the two dozen correct
phrasings to accept. Ancestry and ref position are what actually discriminate.

Also confirmed: the fixture produces identical SHAs across runs
(`c1=d2261fe`, `c2=2b5faf7`, `c3=42dc386`), and every line of all three `.cmds`
files passes the command policy — so the §5.3 fidelity guarantee holds in
practice, not just on paper.

**Second scenario: `content/git/recover-a-lost-commit/`.** Chosen to exercise
the assertion families the first one did not touch — `ref_unchanged`, the
negation case, and recovery. Two commits destroyed by `reset --hard`, with two
branch switches afterwards so the reset is *not* the top reflog entry and
`HEAD@{1}` is a trap.

| | branch-restored | originals-recovered | on-a-branch | main-untouched |
|---|---|---|---|---|
| `solution.cmds` (reflog, reset onto tip) | pass | pass | pass | pass |
| `naive-detached-checkout.cmds` | fail | fail | **fail** | pass |
| `naive-cherry-pick.cmds` | fail | **fail** | pass | pass |
| `naive-reset-main.cmds` | fail | fail | pass | **fail** |

Each counter-example fails its declared check, and the cherry-pick row repeats
the revert scenario's lesson in a different key: the files are byte-identical
and the commit messages match, but the hashes differ (`c2b9c97` vs `a4eeb2e`)
because the work was *rebuilt* rather than recovered. `originals-recovered` —
an ancestry assertion — is the only thing that can tell those apart.

**Verdict on the vocabulary.** It expressed all six checks of the first
scenario and all five of the second with no additions. It needed one
*structural* change (uniform `not:`, §6.3) and produced two asserts that have
not yet justified their existence. That is a vocabulary worth building on.

---

## 7. The kata engine

Simpler, because the oracle is obvious.

1. Workspace receives `solution.py` (your source), `tests.py` (hidden),
   `conftest.py`, `pytest.ini`, and a **copy of** `practice_report.py`. The
   plugin file is copied in rather than imported from the app package, because
   the module has to be importable from the workspace — copying it is what lets
   the subprocess stay isolated.
2. Run with `sys.executable` (the app's own interpreter) in **isolated mode**.
   The invocation below is the one that works; the first draft of this section
   had one that cannot, and every difference was found by running it (§16):

   ```
   python -I -X utf8 -m pytest tests.py \
       -c pytest.ini -p no:cacheprovider -q --no-header --color=no \
       --report-out report.json
   ```

   - `-I` suppresses user site-packages and `PYTHONPATH`, so a stray
     environment variable on your machine cannot change how a kata grades.
   - **The plugin cannot be loaded with `-p`.** `-I` implies `-P`, so the
     workspace is not on `sys.path` when pytest resolves plugin arguments, and
     the import fails before collection starts. The copied-in `conftest.py`
     registers it through `pytest_plugins` instead — by which point pytest has
     imported the conftest by path — and puts the workspace on `sys.path`
     explicitly, which is also what lets `tests.py` do `from solution import …`.
   - **`-X utf8`, not `PYTHONIOENCODING`.** `-I` implies `-E`, which drops every
     `PYTHON*` variable; the sandbox pins `LC_ALL=C` for git's sake, and under
     an ASCII locale a non-ASCII character in an assertion message raises inside
     pytest's own reporting.
   - **`-c pytest.ini` pins the rootdir.** Otherwise pytest walks *upwards* from
     the workspace looking for a config file and obeys the `addopts` of any
     project that happens to be an ancestor of the user cache directory —
     including this one, whose `addopts` carries `--cov`.
   - **`--color=no` keeps ANSI escapes out of a verdict.** pytest colours
     assertion diffs from `TERM` even through a pipe, so without it
     `assert (0, 0) == (1, 2)` arrives wrapped in escape codes and gets stored
     in a `CheckReport`. The same problem `color.ui=false` solves for git.
3. The plugin writes one JSON record per test (nodeid, outcome, message,
   location, duration, docstring). **Written ourselves rather than pulling in
   `pytest-json-report`** — it is ~40 lines, removes a dependency, and produces
   exactly the shape we want.
4. Each test maps to one `CheckReport`, using the test's docstring as the
   human-readable `label` when present.
5. Timeouts are enforced at the subprocess level, not via `pytest-timeout`.
6. **A suite that produced no records is one failing check, not none and not
   all of them.** A collection error or a timeout says nothing about any
   individual assertion, and `Verdict` refuses to be built empty — so the engine
   reports a synthesised `suite-ran` check carrying the captured output. Telling
   a solver that every test failed when the truth is that their file does not
   import sends them looking in the wrong place.

**Complexity self-reporting.** Before submitting, you declare the time and space
complexity of your solution. It is stored on the `Attempt` and compared against
the exercise's declared expectation, but **it is not auto-graded** — static
Big-O analysis of arbitrary code is not something to pretend to do. If your
claim disagrees with the expectation, the verdict surfaces both and makes you
reconcile them. Prompting the right thinking beats faking a grader.

**Known limitation, stated honestly:** `subprocess.run(timeout=...)` kills the
direct child only. A solution that spawns grandchildren could orphan them.

The platform mitigations are genuinely asymmetric, and it is worth being precise
because the obvious Windows answer is wrong:

- **POSIX:** `start_new_session=True` plus `os.killpg(os.getpgid(pid), SIGKILL)`
  reliably takes the whole tree.
- **Windows:** `CREATE_NEW_PROCESS_GROUP` does **not** help here — it exists so
  you can send `CTRL_BREAK_EVENT`, and `Popen.kill()` still terminates only the
  direct child. Killing a tree requires assigning the child to a **Job Object**
  (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) or shelling out to
  `taskkill /T /F /PID`. The Job Object is the correct answer; `taskkill` is the
  pragmatic one.

Accepted as low-risk for single-function katas, with `taskkill /T /F` as the v1
Windows implementation. Written up in ADR 0005.

---

## 8. Sandbox, safety, and the web surface

### 8.1 Isolation model

This is not a security boundary against a determined attacker — you author all
the content and it runs on your own machine. It **is** a correctness and
blast-radius boundary, and being precise about that distinction is itself a good
interview answer.

- **Workspace root:**
  `platformdirs.user_cache_dir("swe-practice")/ws/<short-id>`, where
  `short-id` is the first 8 hex characters of the attempt id. Chosen over the
  system temp dir so a failed attempt survives for inspection, and kept short
  deliberately: **Windows `MAX_PATH` is 260 characters** unless long paths are
  enabled, and a full 36-character UUID plus a nested fixture tree gets
  uncomfortably close. Belt and braces — `core.longpaths=true` is also set in
  the workspace config.
- **Scoped git environment** — the single most important detail:
  `HOME`/`USERPROFILE` → workspace, `GIT_CONFIG_GLOBAL` → a workspace gitconfig,
  `GIT_CONFIG_NOSYSTEM=1`. Your real git config, aliases, and `pull.rebase`
  setting cannot leak in and make a fixture behave differently on your machine
  than in CI. The full pinned set is in §6.1.
- **No network.** `GIT_TERMINAL_PROMPT=0`, no credential helper, and every
  "remote" is a local bare repo inside the workspace.
- **No interactive editors.** `GIT_EDITOR=false` and `GIT_SEQUENCE_EDITOR=false`.
  Without these, `git commit` with no `-m` launches an editor, finds no TTY, and
  **hangs until the timeout expires** — a confusing 10-second stall you would
  otherwise hit within the first five minutes of using the tool. Failing fast
  with a readable error is far better teaching.
- **Trust split** — the load-bearing idea: **fixtures are trusted code, user
  commands are untrusted input.** Fixtures run under Git Bash with a real shell.
  User commands are `shlex.split`, checked against a per-exercise allowlist, and
  rejected if they contain ``| > < & ; $( ` ``.
- **Virtual commands.** Because user input gets no shell, `echo x > file` does
  not work. Rather than re-admitting shell parsing, a handful of file operations
  are implemented in Python and exposed as commands: `write`, `append`, `rm`,
  `mkdir`, `cat`, `ls`. Cross-platform for free, and it keeps the input surface
  tiny.
- **Limits:** 10s per command (configurable per exercise), a total attempt
  budget, 64 KB stdout/stderr caps with truncation markers.
- **Line endings are a repo-level prerequisite.** `.gitattributes` must carry
  `*.sh text eol=lf` (and `*.cmds text eol=lf`) *before the first fixture is
  written*. A `fixture.sh` checked out with CRLF on Windows fails in bash on the
  stray `\r`, with an error message that points nowhere near the real cause.
  Cheap up front, genuinely nasty to debug later.

**Attempt lifecycle.** An attempt is `active` until it is submitted or
abandoned, and its workspace lives exactly that long. Two rules make restarts
and cleanup safe:

- On startup, any attempt still `active` from a previous process is offered for
  **resume** (its workspace is still on disk) or explicitly **abandoned**. An
  interrupted session is neither silently lost nor silently resurrected.
- `practice gc` defines an orphan precisely: **a workspace directory with no
  corresponding `active` attempt row.** Without that definition, "collect
  orphans" would happily delete the workspace of a session you have open in
  another tab.

### 8.2 Offline assets

Offline means **vendoring everything**. No CDN links, at all.

- `htmx.min.js` — single file, trivially vendored.
- **CodeMirror 5, not 6.** CM6 is ESM and needs a bundler, which would drag an
  npm toolchain into a Python project for one widget. CM5 ships a single
  `codemirror.js` + `codemirror.css` plus mode files and drops straight in. CM5
  is in maintenance mode — a real tradeoff, recorded in ADR 0010 — but it is
  fully capable here, and the zero-build property is worth more than being
  current.
- `tools/vendor_assets.py` downloads pinned versions and verifies recorded
  SHA-256 hashes. Run once; output is committed.
- **Enforced by test:** `tests/web/test_offline.py` greps every template and
  static file for `http://`, `https://`, and `//cdn`, and fails the build on a
  hit. Exactly the kind of rule that silently rots without a test.

### 8.3 Web security on localhost

The server executes arbitrary code by design. Two guards, both small:

1. **Loopback binding.** Startup asserts the host is `127.0.0.1`, with a test
   that fails if a future change binds `0.0.0.0`.
2. **Cross-origin guard.** Binding to localhost does *not* stop a malicious
   website in your browser from POSTing to `http://127.0.0.1:8765`. Middleware
   rejects mutating requests whose `Origin` is not our own and whose
   `Sec-Fetch-Site` is not `same-origin`. Cheap, effective, and a good thing to
   be able to explain — most people assume localhost is automatically safe.

### 8.4 Pages

| Route | Contents |
|---|---|
| `/` | Dashboard: due today, streak, recent attempts, weakest tags |
| `/browse` | Filterable exercise list (kind, difficulty, tag, status) |
| `/attempt/{id}` | The workbench — kata editor, or scenario console + state panel |
| `/progress` | Mastery by tag, attempt history, time trends |

HTMX fragments return HTML, not JSON: `POST /api/attempt/{id}/command` renders
the appended command output **and** the re-rendered repo state panel in one
response. Charts are **hand-rolled inline SVG generated in Python** — zero
dependencies, fully offline, fully server-rendered.

The **repo state panel** is the piece that makes git scenarios teachable: HEAD
(and whether it is detached), local and remote branches, a `status` summary,
stash count, and a commit graph. Phase 8 ships a styled text graph built from
structured `git log` data; the SVG lane renderer follows in the same phase once
the DAG model is proven.

---

## 9. Testing strategy

Layered deliberately, fast at the bottom.

1. **Domain / application unit tests** — pure, no I/O, whole suite in
   milliseconds. Coverage gate: **90% on `domain/` and `application/`.** Because
   the check functions live in `domain/checks/` (§6.2), the 22 assertions fall
   inside this gate rather than outside it — which was the whole point of
   putting them there.
2. **Architecture test** — AST-walks `domain/` and `application/`, fails on any
   import from `adapters/` or `interface/`. See §3.
3. **Check-engine tests** — all 22 assert types against `FakeRepoQuery`. No git
   required.
4. **Adapter integration tests** — real git in real temp dirs, real SQLite.
   Marked `@pytest.mark.integration`. Includes a conformance suite asserting
   `GitRepoQuery` and `FakeRepoQuery` agree.
5. **Content integrity tests** — parametrized over every exercise on disk. The
   suite that keeps a 70-exercise library honest:
   - the file validates against the schema;
   - every `assert:` name is registered;
   - katas: `solution.py` **passes** and `stub.py` **fails** (a test suite that
     passes an empty stub is a broken test suite);
   - scenarios: the fixture runs clean, `solution.cmds` passes all `required`
     checks **when replayed through the real command policy**, and each
     counter-example fails **exactly the checks it declares** in
     `expect_failures` — catching both assertions too loose to tell right from
     wrong, and counter-examples that have quietly rotted;
   - at least one `required` check exists, and every reference command is legal
     under the exercise's own `allowed_commands`;
   - hints and notes are non-empty.
6. **Web tests** — `TestClient` plus fragment assertions; the offline-asset test.
7. **Property tests** (hypothesis) on the scheduler: `ease` never drops below
   1.3; consecutive `GOOD` strictly increases the interval; `AGAIN` always
   resets to ≤ 1 day; `due_on` is always after `last_reviewed_at`.
   Note the monotonicity property only holds if the implementation clamps with
   `max(previous + 1, round(interval * ease))` — at the floor of `ease = 1.3`,
   `round(1 × 1.3) == 1`, so a naive multiply leaves the interval unchanged and
   the property test fails on its own stated invariant. Worth writing the test
   first and watching it catch this.
8. **E2E smoke** — one kata and one git scenario driven all the way through the
   CLI adapter.

**CI** (GitHub Actions): matrix `ubuntu-latest` × `windows-latest` on Python
3.13 — ruff, `mypy --strict`, unit, integration, content validation. Windows is
in the matrix from Phase 0 because that is the primary dev machine, and path and
subprocess bugs are exactly what CI should catch early.

---

## 10. Repository layout

```
swe-practice/
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .gitattributes                   # *.sh / *.cmds text eol=lf — see §8.1
├── README.md
├── docs/
│   ├── PLAN.md
│   ├── CONTRIBUTING-CONTENT.md      # how to author an exercise
│   └── adr/0001..00NN-*.md
├── src/practice/
│   ├── domain/
│   │   ├── ids.py  exercise.py  attempt.py  verdict.py  review.py
│   │   ├── ports.py  errors.py  commands.py
│   │   ├── checks/          # registry + 22 PURE assert functions (§6.2)
│   │   │   ├── registry.py  refs.py  trees.py  worktree.py
│   │   │   └── recovery.py  process.py
│   │   └── scheduling/sm2.py
│   ├── application/
│   │   ├── dto.py  registry.py  errors.py
│   │   └── use_cases/*.py
│   ├── adapters/
│   │   ├── content/{schema,loader,validation,filesystem,errors}.py
│   │   ├── persistence/memory.py        # in-memory attempts; sqlite/ in phase 6
│   │   ├── persistence/sqlite/{connection,migrations/,attempts,reviews,mappers}.py
│   │   ├── sandbox/{workspace,provisioner,command_policy,virtual_commands,env}.py
│   │   │            {execution,fixture_runner,fixture_lock}.py  # §16
│   │   ├── git/{repo_query,graph}.py   # reads repos; phase 5
│   │   ├── kata/{pytest_runner,report_plugin,grader}.py
│   │   └── clock.py  ids.py
│   ├── interface/
│   │   ├── web/{app,security}.py + routes/ templates/ static/
│   │   └── cli/main.py
│   ├── composition.py
│   └── config.py
├── content/
│   ├── _lib/fixture_lib.sh          # commit_as, mkremote, publish, write_file
│   ├── fixtures.lock                # cross-platform SHA verification (phase 3)
│   └── {katas,git}/…
├── tests/{unit,integration,content,web,e2e,fakes}/
└── tools/vendor_assets.py
```

---

## 11. Phases

Sequenced so every phase ends with something runnable. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/) — worth doing
because it makes the git history itself part of the portfolio.

**Each phase's commit list is a dependency order, and every commit in it has to
be green on its own.** Not a style preference: a history where commit 3 cannot
import commit 1 is a history you cannot bisect, cannot review one commit at a
time, and cannot use as the portfolio artifact this project is partly for.

The rule is here because Phase 3's list broke it and nobody noticed until the
commits were written. Its commit 1, "workspace provisioning with a scoped git
environment", needed the fixture runner from its commit 4; two of its test files
needed fixtures that the list placed two commits later. The lists below read as
a sensible narrative order — foundations, then the interesting part — and
narrative order is not dependency order. **So check each list against the actual
imports before committing to it, and reorder rather than reaching for a
`--no-verify`-shaped workaround.**

**Verify it in two tiers.** The first draft of this rule ran the whole suite
against every commit, which is thorough and costs about four minutes per commit
— half an hour for a seven-commit phase, every time the split is adjusted. That
is enough friction to make the check something you skip, which is worse than a
cheaper check you actually run. So:

*Per commit* — lint, format, types, and only the tests that commit touches:

```bash
for sha in $(git rev-list --reverse <base>..HEAD); do
  git checkout --quiet --detach "$sha"
  paths=$(git show --name-only --format= "$sha" | grep '^tests/' | xargs -r dirname | sort -u)
  uv run ruff check . && uv run ruff format --check . && uv run mypy \
    && { [ -z "$paths" ] || uv run pytest -q --no-cov $paths | tail -1; }
done
```

Seconds rather than minutes, and it still catches the defect the rule exists
for. **`mypy` is what does most of that work**: a commit whose module imports
something a later commit adds fails the type check in isolation, by name and
line, without running anything. A targeted `pytest` over that commit's own test
directories catches the rest — a collection error in a file the commit added.

*Before a push* — the whole suite with the coverage gate, once, over the final
tree:

```bash
uv run pytest --cov --cov-report=term-missing
```

That is also exactly what CI runs on both platforms, so the per-commit tier is
a bisectability check and the pre-push tier is the correctness one. Neither
substitutes for the other, and only one of them needs to be fast.

Three caveats on the per-commit loop. Run it in the working tree rather than in a
`git worktree`: an editable install resolves `practice` to the path it was
installed from, so a worktree runs the *working tree's* source against the
*commit's* tests and reports failures that are artifacts of the method. (This
applies to `pytest`; `ruff` and `mypy` are static and are safe in a worktree.) And
the tree must be clean — an untracked file from a later commit is still on disk
after `git checkout` and contaminates the run the same way.

The third was found in Phase 5 and is the one that changes how the output should
be read. **The commit the loop blames is not necessarily the commit at fault.**
`paths` is derived from the test directories a commit *touches*, so a commit that
breaks a test somewhere it did not touch passes its own check in silence, and the
failure surfaces on the next commit that happens to touch that directory. Phase
5's commit 7 changed an error message and broke an integration test two
directories away; the loop reported it against commits 8 and 9. `mypy` cannot
help — the break was a string assertion, not a type.

So when the cheap tier goes red, **re-run the failing files across the whole
range** before amending anything:

```bash
for sha in $(git rev-list --reverse <base>..HEAD); do
  git checkout --quiet --detach "$sha"
  echo "$(git log --format='%h %s' -1)"
  uv run pytest -q --no-cov <the files that failed> 2>&1 | tail -1
done
```

That is seconds per commit and it is what attributes the defect. Widening `paths`
instead — running every suite a changed *source* module could reach — is the
obvious alternative and the wrong one: working out which suites a module reaches
is the problem the pre-push tier already solves by running all of them.

**The shape it misses is always the same one**, now that it has happened in two
consecutive phases: a test asserting on a *string* — an error message, a refusal, a
caveat — in a directory the commit did not touch. Phase 5's commit 7 changed an
error message; Phase 6's commit 5 turned a `gc` refusal into a collection and left
a test matching the literal `"phase 6"`. `mypy` cannot see either, because neither
is a type. So: **after changing any user-facing string, grep for it** before
trusting a green cheap tier. One `grep -rn` is cheaper than either the full suite or
the attribution loop, and it is the only check that covers this case directly.

**Effort** is in *sessions* ≈ 2–3 focused hours, at entry-level pace.
**Phases 0–9 (the MVP) total ~40 sessions, so on the order of 100 focused
hours.** That is a real project, not a weekend. Phase 11 roughly doubles it.

Phases 3 and 5 carry the widest error bars — they are the ones with genuine
unknowns (cross-platform subprocess behaviour, and 22 assertions against two
`RepoQuery` implementations). If a phase is going to run over, it is one of
those two.

Phase 3 came in on its six-session estimate, but not where the estimate expected
it: the Windows papercuts §13 flagged as the high risk each cost minutes rather
than the forecast hour, because a fifteen-minute spike found them before any
module existed. The time went instead on semantics nobody had written down, and
on splitting the work into commits that each stand alone. **Budget for the
commit split.** It is not free, and on Phase 3 it paid for itself twice by
finding two ordering defects.

---

### Phase 0 — Foundations · 2 sessions

Scaffolding and the decision record. Boring; sets the tone for everything after.

- `uv init`, `src/` layout, `pyproject.toml`, ruff + mypy strict config
- `.gitignore` and **`.gitattributes` with `*.sh text eol=lf`** — before any
  fixture exists, per §8.1
- pytest config with `unit` / `integration` / `content` markers, plus the
  coverage gate on `domain/` and `application/`
- GitHub Actions matrix (linux + windows) from day one
- ADR template and the first three decisions

**Commits**
1. `chore: scaffold project with uv, ruff, mypy and pytest`
2. `ci: add lint, type and test workflow for linux and windows`
3. `docs: add ADR process and decisions 0001-0003`

**Exit:** `uv run pytest` and `uv run mypy src` pass green in CI on both OSes.

---

### Phase 1 — Domain core · 3 sessions

Pure domain. No adapters, no I/O. The phase that makes or breaks the
architecture story.

- Value objects, `Exercise` + spec union, `CheckSpec`
- `Attempt` aggregate with full lifecycle invariants
- `Verdict` / `CheckReport` with pure `Outcome` derivation
- All ports as `Protocol`s
- The architecture boundary test

**Commits**
1. `feat(domain): add identifiers, exercise and check value objects`
2. `feat(domain): add Attempt aggregate with lifecycle invariants`
3. `feat(domain): add verdict assembly and port protocols`
4. `test(arch): fail the build if the domain imports an adapter`

**Exit:** domain tests pass importing nothing outside the stdlib, and the
boundary test demonstrably fails when you deliberately add a bad import.

---

### Phase 2 — Content model and loader · 3 sessions

- Pydantic schema for both exercise kinds, with helpful error messages
- `FilesystemContentRepository`
- Three real exercises: one kata, two git scenarios
- Content integrity test harness (schema + registry coverage)
- `practice validate` CLI command

**Commits** (as shipped; §16 records why the order differs)
1. `feat(domain): add the assertion registry and command-line policy`
2. `feat(content): add pydantic schema for exercise files`
3. `feat(content): add filesystem content repository`
4. `content(katas): add the two-sum kata`
5. `feat(cli): add practice validate command`
6. `test(content): validate every exercise on disk`
7. `docs: add ADR 0004 and mark phase 2 complete`

**Exit:** `practice validate` passes on all three exercises and fails with a
clear, located message on a deliberately broken file. **Met** — 2026-09-30.

**Sequencing note:** the *schema* half of the content integrity suite lands
here, but the *replay* half — proving `solution.cmds` passes and `naive.cmds`
fails — needs the sandbox (Phase 3) and `RunScenarioCommand` (Phase 5). Until
then the git scenarios are structurally validated but not yet proven solvable.
Don't mistake green here for content that works. *Phase 3 took half of this:
every fixture now runs and every reference list is replayed through the real
sandbox by `tests/content/test_fixtures.py`. What is still unproven is whether
the resulting end state passes the checks — which is grading, and is Phase 5.*

---

### Phase 3 — Sandbox · 6 sessions

The riskiest phase on Windows. Do it early, while it is cheap to change — and
budget for it honestly, because most of §8.1 is Windows papercuts that each cost
an hour to diagnose.

- Workspace provisioning with short paths, scoped git env, disposal
- **The full pinned environment from §6.1**: `core.fileMode`, `core.autocrlf`,
  `core.eol`, `init.defaultBranch`, `core.longpaths`, `GIT_EDITOR=false`,
  `GIT_SEQUENCE_EDITOR=false`, `GIT_CONFIG_NOSYSTEM=1`
- Git Bash discovery for fixtures; argv-list execution, never `shell=True`
- Command policy (allowlist + metacharacter rejection)
- Virtual file commands
- Fixture runner: deterministic SHAs, `commit_as` alias library, ref snapshot
- Workspace lifecycle: explicit `dispose()`, `attach()` to reopen a workspace
  without re-running its fixture, plus a filesystem-only `practice gc
  --dry-run`. The DB-aware orphan definition and the resume-or-abandon *prompt*
  from §8.1 need the attempt table, so they land in Phase 6 — until then `gc`
  only ever reports, and `--no-dry-run` is refused with the reason rather than
  accepted and ignored (§16).

**Commits** (as shipped; the planned order was not a dependency order — see the
rule at the top of this section and §16)
1. `feat(sandbox): add a scoped git environment and a process executor`
2. `feat(sandbox): add command policy and virtual file commands`
3. `feat(sandbox): provision workspaces with a pinned git config and a fixture`
4. `feat(sandbox): add the fixture lock that pins commit hashes across platforms`
5. `feat(cli): add practice fixtures and practice gc`
6. `test(content): run every fixture and replay every reference solution`
7. `docs: add ADR 0005 and mark phase 3 complete`

The planned list opened with workspace provisioning, which needs the fixture
runner it placed fourth and the command policy it placed third. What shipped
runs bottom-up instead: the environment and the executor, then the policy and
the virtual commands that gate what reaches them, then the workspace and
provisioner that compose all four. The two halves of the pinned environment —
the process env and the workspace gitconfig — land with the code that writes
each, rather than as a separate "pin git config" commit that would have had
nothing to pin yet.

**Exit:** the same fixture produces **byte-identical commit SHAs** on Windows
and Linux CI. Prove it by having both jobs write their SHAs and compare against
a committed `content/fixtures.lock`, **not** by hard-coding a literal SHA in a
test — that way a git upgrade that changes hashing shows up as an explicit
lockfile diff you review, rather than a mystery red build. **Met** —
2026-10-01, via `practice fixtures --check` on both runners. §16 records the
five findings and the two deviations.

---

### Phase 4 — Kata engine, first vertical slice · 3 sessions

First end-to-end value. You can solve a kata after this phase.

- pytest report plugin + subprocess runner with timeouts
- `KataGrader` mapping test results to `CheckReport`s
- `StartAttempt`, `SubmitSolution` use cases
- An in-memory `AttemptRepository`, because `StartAttempt` saves through that
  port and SQLite is Phase 6. Not scaffolding to be thrown away: it is the
  second implementation that keeps the port honest under the §13 rule, and the
  one every application test will use long after SQLite lands.
- **`composition.py`** — the single wiring point from §3, which has to exist as
  soon as there is an object graph to build.
- CLI: `practice solve katas/two-sum`

**Commits** (as shipped; two deviations from the planned list, both in §16)
1. `feat(kata): add pytest report plugin and sandboxed runner`
2. `feat(kata): add grader mapping test results to check reports`
3. `feat(app): add the grader registry, in-memory attempts and the root`
4. `feat(app): add StartAttempt and SubmitSolution use cases`
5. `feat(cli): solve a kata end to end from the terminal`
6. `test(content): grade every kata's reference solution and its stub`
7. `docs: mark phase 4 complete`

Commit 3 carries the grader registry as well, because `composition.py` cannot
assemble `Services` without one — the registry is an edge in the graph the
wiring module exists to show. Commit 6 is separate because it is the *exit
criterion* rather than the engine: it shrinks `unproven_by_design`, which trips
the Phase 2 tripwire in `tests/content/test_library.py` and makes the build fail
until someone writes the grading tests.

**Exit:** a kata solved from the terminal, correctly passing and correctly
failing, with the content test proving stub fails and reference passes.
**Met** — 2026-10-01. `practice solve katas/two-sum --reference --time "O(n)"
--space "O(n)"` exits 0 with ten green checks; the same command with no source
grades the shipped stub, prints nine failures and exits 1; a git scenario is
refused with the phase that lands it. §16 records the five findings and the six
deviations.

---

### Phase 5 — Git scenario engine · 9 sessions

The heart of the project, and by a wide margin the longest phase. Two
`RepoQuery` implementations, 22 assertions with tests, a conformance suite and
two use cases is simply a lot of surface — the earlier 5-session estimate was
wishful.

- `GitRepoQuery` adapter and `FakeRepoQuery` fake. The **port** is already
  there — Phase 1 shipped every protocol in `domain/ports.py`, and
  `RepoQuery`'s vocabulary types with it — so this phase adds implementations,
  not the interface.
- Conformance suite proving the two implementations agree
- Ref and tree assertions, and the registry **turned into a dispatch table**.
  `domain/checks/registry.py` already exists as the set of legal `assert:`
  names, which is what lets the Phase 2 schema reject a typo; this phase makes
  it `name -> CheckFunction` and keeps `is_registered` working unchanged.
- Worktree, index, stash, reflog assertions
- Advisory/process assertions over the attempt event log
- `ScenarioGrader` behind the `Grader` port, assembling `CheckReport`s into a
  `Verdict` — the piece the original list skipped between the assertions and
  the use cases. `SubmitScenario` cannot grade without it, and it is what makes
  the kind registry in §3 dispatch to something.
- `RunScenarioCommand`, `SubmitScenario` use cases
- **Graded replay**, which completes the content integrity suite deferred from
  Phase 2. Phase 3 already replays both through the real policy and asserts they
  *run*; what is still missing is the oracle — `solution.cmds` must pass every
  `required` check, and each counter-example must fail **exactly** the checks
  its `expect_failures` declares. That last word is the whole point: "fails at
  least one check" would let a counter-example rot into failing for an
  unrelated reason with CI none the wiser (§5.4).
- CLI scenario driver
- **Spike:** whether `rebase -i` is drivable with a non-interactive
  `GIT_SEQUENCE_EDITOR` stand-in. Decide this *before* promising `rebase -i`
  content in Phase 11.

**Commits** (bottom-up: implementations, then assertions over them, then the
grader that assembles those, then the use cases, then the drivers)
1. `feat(git): add a git RepoQuery adapter and an in-memory fake`
2. `test(git): add conformance suite for RepoQuery implementations`
3. `feat(checks): dispatch the registry, with ref and tree assertions`
4. `feat(checks): add worktree, stash and reflog assertions`
5. `feat(checks): add advisory assertions over the command log`
6. `feat(checks): assemble check reports into a scenario verdict`
7. `feat(app): add RunScenarioCommand and SubmitScenario use cases`
8. `test(content): grade every reference solution and counter-example`
9. `feat(cli): solve a git scenario end to end from the terminal`

Nine commits against nine sessions is a coincidence, not a plan — the spike
above is a session that produces no commit, and commits 3–5 are the bulk of the
22 assertions and will take more than one each.

**Exit:** the revert-a-pushed-commit scenario passes via `revert`, and
`reset --hard` fails the `history-preserved` check with a useful explanation.
That contrast **is** the product working.

**Met** — 2026-10-01. Both halves, from a terminal:

```
practice solve git/revert-a-pushed-commit --reference            -> PASS, exit 0
practice solve git/revert-a-pushed-commit -c naive-reset-force.cmds
    ok   The committed tree matches the state before the bad commit
    FAIL The bad commit is still reachable — you did not rewrite published history
         expected @c3 (bab6eca) reachable from HEAD (dc52587), got not reachable
         Your teammate already has c3. If it stops being an ancestor of `main`, ...
    note You did not force-update a shared branch
                                                                 -> FAIL, exit 1
```

Three answers, one tree. The content check passes for all of them, the ancestry
check is what discriminates, and the force-push is flagged without failing the
attempt. §16 records what the phase found.

---

### Phase 6 — Persistence · 3 sessions — **complete**

- SQLite connection (WAL, `foreign_keys=ON`), numbered SQL migration runner
- `SqliteAttemptRepository` with explicit row↔domain mappers
- `SqliteReviewRepository`
- Swap the in-memory repositories for the SQLite ones in `composition.py`,
  which Phase 4 created. One line per repository if the ports have been
  respected — and if it is not, that is the finding.
- **Attempt lifecycle completed:** resume-or-abandon on startup, and `gc`
  promoted from reporting to real deletion now that "orphan" can be defined
  against the attempt table (§8.1). `SubprocessSandboxProvisioner.attach`
  already exists from Phase 3; what is missing is the table that says which
  workspace is still in use.

**Commits**
1. `feat(db): add sqlite connection and migration runner`
2. `feat(db): add attempt repository with explicit mappers`
3. `feat(db): add review card repository`
4. `refactor: swap the in-memory repositories for sqlite at the root`
5. `feat(app): add attempt resume and db-aware workspace gc`
6. `docs: add ADR 0006 and mark phase 6 complete`

**Exit:** attempts survive a restart and can be resumed; migrations apply
cleanly from empty and are idempotent; `gc` provably never deletes the
workspace of an active attempt. **All three met** — the first by four `practice`
invocations sharing one attempt in `tests/e2e/test_resume_an_attempt.py`, the
second by applying the shipped migrations to an empty file and then to itself,
and the third by `test_gc_never_collects_the_workspace_of_an_active_attempt`
asking for the delete and getting none.

The commit list needed one addition that is recorded in §16 rather than edited
away: **`practice start`**, without which the other lifecycle commands have no
reachable state to act on. `solve` starts and submits in one process, so nothing
it does leaves an attempt open.

---

### Phase 7 — Web shell and kata workbench · 4 sessions

- FastAPI app, base templates, loopback assertion, cross-origin middleware
- Vendored htmx + CodeMirror with a hash-pinned fetch script
- `/browse` and the kata workbench
- HTMX submit flow with a verdict panel

**Commits**
1. `chore(web): vendor htmx and codemirror for offline use`
2. `feat(web): add FastAPI app, base templates and loopback guard`
3. `feat(web): add browse and kata workbench pages`
4. `feat(web): add htmx submit flow with verdict panel`

Vendoring comes first because the base template references the vendored files by
path. The other way round, commit 1 ships a layout whose `<script>` 404s —
which the offline-asset test would not catch, because it greps for `http://`
and a broken local path is not a remote one.

**Exit:** a kata solved entirely in the browser with the network disconnected.
Offline-asset test green.

---

### Phase 8 — Git scenario workbench · 4 sessions

- Command console with HTMX-appended history
- Repo state panel: HEAD, refs, status, stash
- Commit graph — text lanes first, then the SVG renderer
- Progressive hint reveal and verdict breakdown with explanations

**Commits**
1. `feat(web): add scenario command console with htmx history`
2. `feat(web): render repo state panel with refs and status`
3. `feat(web): add commit graph renderer`
4. `feat(web): add hint reveal and verdict breakdown`

**Exit:** a git scenario driven start to finish in the browser, with the graph
visibly changing after each command.

---

### Phase 9 — Spaced repetition and progress · 3 sessions

Turns a quiz app into a training system.

- SM-2 (four-grade Anki variant) as a pure function, with property tests —
  including the `max(previous + 1, ...)` interval clamp the monotonicity
  property requires (§9, item 7)
- Review queue plus an auto-suggested grade from verdict, elapsed time and hints
  used
- Dashboard: due queue, streak, weakest tags
- Progress page with inline-SVG charts

**Commits**
1. `feat(domain): add SM-2 scheduler with property tests`
2. `feat(app): add review queue and grade suggestion`
3. `feat(web): add dashboard with due queue and streak`
4. `feat(web): add progress page with tag mastery charts`

**Exit:** "what should I practice today?" is answered by the tool, not by you.

**MVP ends here.** Phases 0–9 are a complete, genuinely useful product.

---

### Phase 10 — Own-editor mode · 2 sessions

- Scaffold the kata into a real file on disk; reveal it in the editor
- `watchfiles` watcher plus an SSE endpoint that re-grades on save

**Commits**
1. `feat(workspace): add file mode scaffolding and reveal in editor`
2. `feat(web): stream grade-on-save results over SSE`

**Exit:** save in VS Code, see the verdict update in the browser.

---

### Phase 11 — Content build-out · 8+ sessions

The phase that determines whether you actually use this thing. Pure authoring,
no code changes — which is the payoff of §5.

Git tracks (~24 scenarios): history rewriting · recovery & bisect ·
collaboration & conflicts.
Kata tracks (~30 katas): arrays/strings/hashing · trees & graphs · DP & greedy.

**Commits**
1. `content(git): add history rewriting track`
2. `content(git): add recovery and bisect track`
3. `content(git): add collaboration and conflict track`
4. `content(katas): add arrays, strings and hashing track`
5. `content(katas): add trees and graphs track`
6. `content(katas): add dynamic programming track`
7. `content: add curriculum manifest with track ordering`

**Exit:** ≥ 50 exercises, all green under the content integrity suite.

---

### Phase 12 — Polish and portfolio artifacts · 3 sessions

- `practice` launcher: first-run setup, migrations, browser open
- README with the architecture diagram and a demo GIF
- Remaining ADRs plus an honest "what I'd do differently" postmortem
- Tag `v1.0.0`

**Commits**
1. `feat: add launcher with first-run setup`
2. `docs: add README with architecture diagram and demo`
3. `docs: add remaining ADRs and a project postmortem`
4. `chore(release): tag v1.0.0`

**Exit:** a stranger can clone, run one command, and be practicing in under two
minutes.

---

### Phase 13 — Stretch (post-v1, pick by appetite)

Each one is intended to be an **adapter or content addition, not a rewrite** —
which is the real test of whether the architecture earned its keep.

| Idea | Touches |
|---|---|
| Docker sandbox adapter | a new `SandboxProvisioner` implementation only |
| FSRS scheduler | a new `Scheduler` implementation only |
| Shell/CLI drills (grep, awk, jq, logs) | new exercise kind + content |
| Concept recall with rubric self-grading | new exercise kind + content |
| Embedded terminal (xterm.js + pty) | a new interaction adapter |
| SQL drills against seeded SQLite | new exercise kind |
| Exportable content packs | a content repository adapter |
| Interview mode (timed, no hints, no test peeking) | application-layer policy |

---

## 12. Architecture decision records

Written as they are decided, not retrofitted. These are the artifacts to bring
to an interview — being able to say *"here is the record where I rejected string
matching, and here is the alternative I would choose if the constraints
changed"* is worth more than any code sample.

| ADR | Decision | Status |
|---|---|---|
| [0001](adr/0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](adr/0002-ports-and-adapters-with-an-enforced-boundary.md) | Ports and adapters, with the boundary enforced by a test | accepted |
| [0003](adr/0003-grade-git-exercises-by-repo-state.md) | Grade git exercises by repo state, not command text | accepted |
| [0004](adr/0004-content-as-declarative-data.md) | Content is declarative data, validated by schema | accepted |
| [0005](adr/0005-sandbox-via-temp-dirs-and-subprocess.md) | Sandbox via a scoped directory and subprocess, not containers | accepted |
| [0006](adr/0006-sqlite-without-an-orm.md) | SQLite with hand-written SQL and explicit mappers, not an ORM | accepted |
| 0007 | HTMX over a single-page app | not yet written |
| 0008 | SM-2 first, FSRS behind a port | not yet written |
| 0009 | Ship our own prompts; never redistribute problem text | not yet written |
| 0010 | CodeMirror 5 over 6, to avoid an npm build step | not yet written |
| [0011](adr/0011-reference-solutions-are-command-lists.md) | Reference solutions are command lists, not shell scripts | accepted |

---

## 13. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Windows subprocess/path bugs | **High** | Windows in CI from Phase 0; argv lists only; sandbox tackled in Phase 3 while cheap to change; 6 sessions budgeted, not 4 |
| Non-deterministic fixture SHAs | Medium | The full pinned set in §6.1 — identity, dates, `fileMode`, `autocrlf`, `eol`, `defaultBranch` — verified against `content/fixtures.lock` on both platforms |
| Assertions too loose to tell right from wrong | **High** | Mandatory `naive.cmds` counter-examples that CI requires to fail, replayed through the real policy |
| Reference solutions validated through a path users cannot use | Medium | §5.3 — solutions are command lists replayed through `RunScenarioCommand`, never shell scripts |
| Content authoring stalls | **High** | This is the real failure mode. Content-as-data plus a documented authoring guide; Phase 2 proves the loop with three exercises before any UI exists |
| Scope creep into SQL/k8s/system design | High | Phase 13 exists precisely to park these |
| Over-abstracting for the interview story | Medium | Every port must have ≥ 2 real or test implementations, or it gets deleted |
| CodeMirror 5 being legacy | Low | Isolated to one template; CM6 + esbuild is a contained swap if needed |

That second-to-last row is worth taking seriously. The fastest way to ruin this
project is to add interfaces because they look impressive. The `Clock` and
`RepoQuery` ports pay for themselves in testability on day one; a
`NotificationService` with one implementation would not.

---

## 14. Interview talking points

Rehearse these; they are the return on the architectural investment.

- **"Walk me through a design decision you made."** Grading git by repo state
  rather than command text. Name all three options, explain why string matching
  is actively harmful (it punishes correct answers it did not anticipate), and
  land on end-state assertions with advisory checks for craft.
- **"How do you test something that depends on an external tool?"** The
  `RepoQuery` port: interrogate through a narrow read-only interface, implement
  it twice (real git, in-memory fake), unit-test all 22 assertions against the
  fake in milliseconds, then run a conformance suite proving the two agree.
- **"How do you keep an architecture from decaying?"** A test that AST-walks the
  domain and fails the build on an inward-pointing violation. Rules without
  enforcement are suggestions.
- **"Tell me about a tradeoff."** CodeMirror 5 over 6: accepting a
  maintenance-mode dependency to avoid dragging an npm build pipeline into a
  Python project for one widget. Or SM-2 over FSRS: ship the simple algorithm
  behind a port, upgrade when there is data to justify it.
- **"What did you leave out?"** The non-goals table in §1 — and *why* each item
  was cut. Deliberate scope control reads as senior.
- **"What would you do differently?"** The Phase 12 postmortem, written honestly
  after building it. Have a real answer, not a humble-brag.
- **A security detail most people miss:** binding to localhost does not protect
  you from a malicious website POSTing to your dev server. Origin and
  `Sec-Fetch-Site` validation, on a tool that executes arbitrary code by design.

---

## 15. Open questions

Not blockers — decide when the phase arrives.

1. **Merge-conflict scenarios** need a mid-attempt editing surface (resolve the
   conflict, then continue). The virtual `write` command takes content as a
   single argv element, so it cannot express multi-line file content or
   embedded quotes — which means the CodeMirror pane is probably *required*
   here, not optional. Decide in Phase 8; the alternative is a
   `resolve <path>` affordance that opens the conflicted file in the editor.
2. **Interactive rebase — spiked in Phase 5. Answer: drivable, and deferred
   past the MVP.** The spike ran against a real provisioned workspace rather than
   reasoning about git, and found four things, two of which the question did not
   anticipate.

   - **`GIT_SEQUENCE_EDITOR` beats `git -c sequence.editor=…`.** A solver cannot
     override the pinned `false` from their own command line; whatever drives
     `rebase -i` has to come from the sandbox.
   - **One stand-in is not enough.** With `GIT_SEQUENCE_EDITOR='sed -i
     2s/^pick/squash/'` the todo list *is* rewritten and the rebase starts —
     `Rebasing (2/2)` — and then dies, because `squash` opens a **commit message**
     editor and `GIT_EDITOR` is also `false`:
     `Please supply the message using either -m or -F option`. Both editors need
     replacing, not one. §8.1 and this question named only the first.
   - **The engine already reads a mid-rebase stop correctly.** `head_ref()`
     returns `None`, `status()` shows the staged half-applied change,
     `.git/rebase-merge` exists. So the state is gradable — but nothing in the 22
     can *say* "a rebase is in progress", and `head_detached` firing is
     technically true and the wrong sentence. An `edit`-plan exercise would need a
     `rebase_in_progress` assertion.
   - **The solver has to choose the plan, or the exercise grades nothing.** If the
     sandbox's stand-in picks `squash`, the exercise is "type one command and the
     tool rewrites history for you". The mechanism that keeps the choice with the
     solver: a sequence editor of `cp <their file>`, since git appends the real
     todo path as the editor's last argument. They write the plan with the virtual
     `write` command and run `git rebase -i HEAD~3` as normal.

   **Decision: no `rebase -i` content in the MVP, and the mechanism is recorded so
   Phase 11 is not guessing.** The cost is three sandbox changes, one new
   assertion, and a new authoring affordance (a plan file), for one family of
   exercises — and `write` taking its content as a single argv element makes a
   multi-line todo awkward in exactly the way open question 1 describes. If the
   CodeMirror pane lands in Phase 8 and solves that, both questions get easier at
   once, which is the right order to take them in.
3. **Kata languages beyond Python.** The runner is already behind a port, so
   adding TypeScript means a `vitest` adapter. Worth it only if you interview
   in TS.
4. **Curriculum sequencing** — hand-ordered tracks, or prerequisite-graph
   unlocking? Start hand-ordered; revisit once there are 50 exercises.

---

## 16. Revision log

**2026-09-30 — review pass.** Sixteen issues found and fixed. The three that
mattered were structural rather than technical:

- **Reference solutions bypassed the command policy.** As first drafted,
  `solution.sh` was a bash script, so CI validated solutions through an
  execution path the user cannot use — proving only that a solution existed,
  not that one existed *within the rules*. A scenario could have shipped
  unsolvable with a green build. Now command lists (§5.3, ADR 0011).
- **`Attempt` could not enforce its own invariants.** It holds an `ExerciseId`,
  not an `Exercise`, so it had no access to `max_commands` or the hint list.
  Fixed with `AttemptPolicy` copied in at construction (§4.3).
- **The check functions were in the wrong layer.** Placed under `adapters/`
  despite being pure functions over a port, which put the most
  correctness-critical code in the project outside the coverage gate. Moved to
  `domain/checks/` (§6.2, §9).

Also corrected: the Windows process-tree kill claim (`CREATE_NEW_PROCESS_GROUP`
does not do this — Job Objects or `taskkill /T /F` do); an incomplete
determinism story that would have broken cross-platform SHAs via `core.fileMode`
and `init.defaultBranch`; and unpinned `GIT_EDITOR`, which would have hung
`git commit` on the first attempt. Estimates for Phases 3 and 5 revised from 4
and 5 sessions to 6 and 9, moving the MVP from ~34 to ~40 sessions.

The pattern worth noticing: the technical errors were cheap — look up the API,
fix the line. The expensive ones were architectural, and all three would have
survived to Phase 11 before doing visible damage.

**2026-09-30 — flagship scenario authored and executed.** Before starting
Phase 0, `content/git/revert-a-pushed-commit/` was written in full and run by
hand against real git to test whether the §6.3 assertion vocabulary could
actually express it. **It could, with no additions** — the main thing this was
meant to find out. Results in §6.6.

Four things the run surfaced that thinking about it had not:

- **The pinned clock only covered the fixture.** User commits during an attempt
  fell back to wall-clock time, so attempts were not reproducible. The clock
  now spans the whole attempt (§6.1).
- **The plan's own example was missing `fix-published`.** A solution that
  reverted locally and never pushed would have passed every check while leaving
  the build broken for the teammate the exercise is about. Fixed in §5.2, and
  now one of the two counter-examples.
- **Resolution grammar and failure semantics were unspecified** — what `target:`
  accepts, and what happens when a named ref does not exist. Both pinned down
  in §6.5, along with `worktree_clean` ignoring untracked files.
- **`@c2` is assertion syntax only.** A content author will reach for it in
  `solution.cmds`, where it cannot work, because the user only ever sees real
  revisions. Belongs in the authoring guide as an explicit warning.

The general lesson, and the reason this was worth doing before Phase 0: three
of the four were invisible on paper and obvious within a minute of running the
thing.

**2026-09-30 — second scenario authored and executed.**
`content/git/recover-a-lost-commit/` (reflog recovery), chosen specifically to
hit the assertion families the revert scenario did not. Solution and all three
counter-examples behave as designed; results in §6.6. Three more findings,
all about the vocabulary rather than the engine:

- **Negation was asymmetric.** Five asserts had negative twins; `head_detached`
  had none, and this scenario needed exactly that. Resolved by making `not:`
  a universal modifier and deleting all six twins — 27 asserts down to 22, and
  one less thing for a content author to guess about. The revert scenario's
  `command_not_used` was migrated to `command_used` + `not: true` so both
  exercises use one mechanism.
- **`command_count` actively fights this exercise.** An "efficiency" budget
  counts read-only commands, so it penalises the same inspection the
  `used-the-reflog` advisory rewards. The check was removed from the exercise
  rather than shipped, with a comment saying why. Along with `reflog_contains`
  — which is either vacuous or grades method, not outcome — it is now flagged
  as unproven and will be deleted if Phase 11 does not need it.
- **"Counter-example fails at least one check" is too weak a contract.**
  Counter-examples referring to `HEAD@{n}` depend on reflog indices that shift
  when a command is added, so an edit could leave one failing for an unrelated
  reason, or passing outright, with CI green. Counter-examples now declare
  `expect_failures: [check-id]` (§5.4).

Two scenarios in, the engine design has not needed a single change — every
finding has been in the content schema or the assertion vocabulary. That is
the right place for churn to land this early, and a reasonable signal that the
§3 boundaries are drawn about right.

**2026-09-30 — Phase 0 complete.** Scaffolding, CI on both platforms, and
ADRs 0001-0003. Exit criterion met: ruff, `ruff format --check`,
`mypy --strict` and `pytest` all green.

Four things worth keeping, all found by running the thing rather than writing
it:

- **`UV_FROZEN` cannot be combined with `uv sync --locked`.** uv rejects the
  pair outright. Both were in the first draft of the workflow, so step one
  would have failed on every CI run. `UV_NO_SYNC=1` gives the property actually
  wanted — one explicit sync, and no later `uv run` quietly re-resolving.
- **`actions/checkout` and `astral-sh/setup-uv` are on v7 and v10**, not the v4
  and v5 written from memory. Worth a habit: never pin an action major from
  recall, check the release.
- **ruff 0.16 formats fenced Python inside Markdown.** `ruff format --check .`
  wanted to reflow this file's aligned-comment pseudo-Python, which is prose,
  not code. `extend-exclude = ["*.md"]`.
- **The coverage gate holds on empty packages.** `domain/` and `application/`
  were created as empty packages in the scaffold commit so the gate measures
  the right two directories from the first commit; coverage reports 100% of
  zero statements and the 90% floor passes. A gate added after the code exists
  gets its threshold tuned to whatever the code already scores.

Two deliberate deviations from §11 as written, both recorded in the commits:
the full runtime dependency set from §2 is declared now rather than phase by
phase, so `uv.lock` is resolved once; and CI runs one pytest invocation instead
of splitting by marker, because pytest exits non-zero on an empty selection and
there are no integration or content tests yet. Markers themselves are applied
by directory in `tests/conftest.py` — a forgotten decorator would silently drop
a test out of every `-m` selector, which is the one failure mode a marker
scheme must not have.

**2026-09-30 — Phase 1 complete.** The pure domain, all ten ports, and the
architecture boundary test. `ruff`, `ruff format --check`, `mypy --strict` and
191 tests green, with `domain/` at **100%** statement and branch coverage against
the 90% gate. Exit criterion checked rather than asserted: adding `import
subprocess` and an adapter import to `domain/ids.py` fails both boundary tests,
each naming the module and line, and they pass again once reverted.

Four findings, and the first two are the ones worth keeping:

- **§11's commit order for this phase does not compile.** It puts verdict
  assembly in the same commit as the ports, *after* the `Attempt` aggregate — but
  `Attempt.complete` takes a `Verdict` and `ports.py` takes an `Attempt`, so the
  only order that builds is verdict → attempt → ports. Split into three commits
  accordingly. A phase plan written from the outside in reads naturally and
  compiles backwards.
- **A port nothing imports at runtime reads as 0% covered.** Every module reaches
  `ports.py` through `TYPE_CHECKING`, so its 42 statements were never executed and
  the gate fell from 100% to 94% the moment the file landed. The fix was not a
  coverage exclusion: `WorktreeStatus.is_clean` encodes the §6.5
  "ignore untracked by default" rule and `CommitInfo.is_merge` is what
  `linear_history` will read, so both wanted real tests anyway. Worth generalising
  — coverage that ignores a file because nothing imports it is not measuring what
  it claims to.
- **`declared_complexity: str | None` cannot do its job.** §7 has the solver
  declaring time *and* space and the verdict surfacing both against
  `ComplexityExpectation`, which has two fields. One string cannot disagree with
  an expectation on only one axis, so it is now a `ComplexityClaim` value object
  with an `agrees_with` that folds away case and spacing.
- **Two linters have opinions about domain vocabulary.** bandit's S105 reads
  `Outcome.PASS = "pass"` as a hardcoded password, and ruff A002 flags any
  argument named `id` or `filter`. The enum members keep their names with a noqa
  and a comment — renaming to `PASSED` to appease a substring match would distort
  the vocabulary — while the *arguments* were renamed (`attempt_id`, `criteria`),
  since the attributes keep the plan's names either way.

Three deliberate deviations from §4 as written, all now folded back into §4.1,
§4.3 and §4.6 so the plan and the repo do not disagree silently:

- Enums live with the concept they describe rather than all in `ids.py`, and are
  `StrEnum` whose values match the YAML — so the loader gets
  `ExerciseKind("git_scenario")` for free and persistence stores something
  readable.
- `domain/review.py` lands now rather than in Phase 9, because `ports.py`
  declares `ReviewRepository` and `Scheduler` and both need the card to exist. The
  SM-2 arithmetic does not. The ease floor of 1.3 is enforced on the card and not
  only inside the scheduler: an invariant that holds because one function is
  currently the sole writer is not an invariant.
- `AttemptStatus` and `abandon()` are included, per §8.1's lifecycle, rather than
  waiting for Phase 6 to retrofit them onto an aggregate whose guards would then
  have to be reopened.

One invariant was placed deliberately, and the line is worth naming because it
will come up again in Phase 2. **Correctness holes are domain invariants; quality
rules are the content suite's job.** A scenario whose checks are all advisory
passes vacuously, and a counter-example naming a check id that does not exist can
never fail the check it claims to — so `GitScenarioSpec` refuses to exist in
either state. "Hints and notes are non-empty" is a rule about a *good* exercise
rather than a *representable* one, so it stays in §9 where the plan put it; the
domain should not refuse to model an exercise someone is halfway through drafting.

**2026-09-30 — Phase 2 complete.** The content schema, the loader, the
filesystem repository, `practice validate`, the first kata, and the content
integrity suite. `ruff`, `ruff format --check`, `mypy --strict` and 385 tests
green, with `domain/` and `application/` at **100%** against the 90% gate. Exit
criterion checked rather than asserted: `practice validate` passes on all three
exercises, and on a deliberately broken file reports every problem at once,
located to the field, exiting 1.

Four findings, and the first is the one to keep:

- **A schema constraint that duplicates a domain invariant makes errors worse,
  not merely redundant.** `checks` carried a Pydantic `min_length=1` alongside
  `GitScenarioSpec`'s own "a scenario needs at least one check". A single
  mistyped assertion then produced *two* errors: the real one, and "Tuple
  should have at least 1 item after validation, not 0" — because the check that
  failed validation had been dropped from the list. An author reads the second
  and goes hunting for a bug that is not there. Removed from all three fields
  that had it; the domain already held every one of those rules. The general
  form is worth remembering: duplicated validation does not just cost
  maintenance, it *generates misinformation*, because the second validator sees
  the wreckage left by the first.
- **The plan's own assertion count was wrong, in two directions at once.** §6.3
  enumerates 22 asserts; the prose said 19, and four other sections said "~25".
  The "25 down to 19" arithmetic in the September review subtracted six twins
  from a total the enumerated list never had. Corrected everywhere to 22 — and
  the registry in `domain/checks/registry.py` is now the single place the
  vocabulary is written down, so the next such drift is a failing test rather
  than a number in prose. A count repeated in six places is a count that will be
  wrong in at least one.
- **§2's stack table had no YAML parser**, although §5 makes content YAML. This
  is exactly why Phase 0's "declare the whole dependency set now" pass missed
  `pyyaml`: it worked from the table, and the table was the thing that was
  incomplete. A summary used as a source of truth inherits every gap in it.
- **Content is code and needs running.** Two of the ten kata tests were wrong on
  first writing, and both were the kind of wrong that ships: one asserted a
  `ValueError` for "no pair exists" when the prompt promises a pair always does
  — grading a correct solution against undefined behaviour — and another used
  `[4, 1, 9]` with a target of 8, a list with no valid pair at all. Neither was
  visible on the page. Both took seconds to find by running the file.

Also found, and noted for Phase 4: **the `python -I -m pytest` invocation in §7
cannot import `solution`.** `-I` implies `-P`, which drops the workspace from
`sys.path`, so `from solution import two_sum` fails before any test runs. The
workspace `conftest.py` that §7 already lists is what has to put it back — worth
knowing now rather than debugging it as a mysterious collection error later.

Five deliberate deviations from §5, §10 and §11, all folded back above so the
plan and the repo do not disagree silently:

- **The commit order in §11 was wrong again**, in the same way Phase 1's was. It
  opens with the schema, but the schema cannot validate an `assert:` name
  without the registry, and the registry is domain code — so the vocabulary and
  the command-line parser land first. A phase plan written outside-in reads
  naturally and compiles backwards; two for two.
- **`adapters/content/validation.py` is a fourth module**, not one of the three
  §10 lists. Loading and auditing are different jobs with different callers:
  browsing the library must not fail because a draft exercise has an empty
  `notes.md`, while `practice validate` must say so. It is the same line §4.2
  draws inside the domain — a correctness hole is a failure, a quality rule is a
  report.
- **§5.2's short counter-example form is rejected outright.** §5.4 supersedes it,
  and accepting `counter_examples: [naive.cmds]` would mean inventing an
  `expect_failures` the author never wrote — which is the weak contract §5.4
  exists to replace.
- **§5.1's `references:` field is not implemented.** Nothing consumes it, and
  `extra="forbid"` means a field that is accepted and then dropped is worse than
  one that does not exist. Attribution lives in `notes.md` prose until a page
  displays it.
- **`composition.py` is deferred.** There is one adapter to construct; a wiring
  module with a single line in it is precisely the abstraction §13 says to
  delete rather than carry. It arrives when there are two things to wire.

One rule was placed, and it is the Phase 2 counterpart to Phase 1's. The content
suite now requires **every `required` check to carry an explanation**, and it
found a real gap the hour it was written: `recover-a-lost-commit`'s
`clean-worktree` had shipped with a label and nothing else. A learner who failed
it would have been told what was wrong and not why — the exact failure §1 exists
to reject, in the project's own content. The rule sits in `tests/content/`
rather than in the schema for the §4.2 reason: an exercise missing an
explanation is representable, and someone may be halfway through drafting it. It
is still not shippable.

Finally, `tests/content/test_library.py` carries a tripwire rather than a
comment. §11 says not to mistake green here for content that works;
`test_the_unproven_guarantees_are_still_unproven` asserts the *count* of things
`practice validate` admits it cannot prove, so when the sandbox lands and that
list shrinks, the build fails and someone has to come back and write the replay
tests. A note in a plan is not a mechanism.

**2026-10-01 — Phase 3 built: the sandbox.** Six sessions budgeted and the
budget was right, though not quite for the predicted reasons. §13 called
"Windows subprocess/path bugs" the high risk; the Windows problems were real but
each cost minutes rather than the forecast hour, because the spike that found
them ran before any module was written. What actually took the time was the
semantics nobody had written down.

Five findings, in rough order of how much they changed:

- **`pwd` had to be a virtual command, and the content already said so.** §8.1
  lists six virtual commands. `content/git/revert-a-pushed-commit` had shipped
  `pwd` in its `allowed_commands` since before Phase 0, and `pwd` is a shell
  builtin with no executable behind it on Windows — so a solver typing a command
  the exercise explicitly permits would have got `command not found`. Found by
  replaying the exercise's own allowlist, not by reading the plan. The virtual
  set is now seven, and a test asserts the set and the dispatch table agree.
- **`rm -rf .` deleted the repository, `.git` and all.** Caught by a test
  written to assert the opposite, which is the best possible way to find it. The
  path guard correctly refused anything *outside* the repository and happily
  accepted the repository itself, leaving an attempt that cannot be graded and a
  failure that looks like a tool bug. Real `rm` refuses this too; matching it
  closed the hole.
- **The clock's constants were defined twice.** `fixture_lib.sh` held its own
  epoch and step, duplicating `adapters/sandbox/env.py`. Two copies would drift
  and the symptom would be every hash in `content/fixtures.lock` moving for no
  visible reason. The provisioner now exports `PRACTICE_EPOCH` and
  `PRACTICE_STEP` and the library reads them, so Python owns the definition and
  bash has none.
- **`gc.auto` had to be pinned, which §6.1's table does not mention.**
  `recover-a-lost-commit` works by recovering commits no ref points at, and git
  starts a background garbage collection on its own once enough loose objects
  accumulate — which is entitled to delete exactly those objects. The exercise
  would have become unsolvable for reasons nobody could reproduce. `gc.auto=0`
  plus disabled reflog expiry are now in the pinned config, and a test asserts
  the recovery fixture really does leave unreachable commits behind.
- **`fixture_runner` could not live under `adapters/git/`** where §10 drew it.
  It reaches into the sandbox's environment, executor and workspace, while the
  provisioner reaches into it — so with both packages re-exporting, they
  imported each other and Python said so. Moved to `adapters/sandbox/`, which is
  also the better line: everything that *builds* a repository is the sandbox,
  and `adapters/git/` is for the half that *reads* one (`GitRepoQuery`, the
  commit graph) in Phase 5. `fixture_lock` moved with it.

Two deliberate deviations from the plan as written:

- **`SandboxProvisioner.provision` takes the `AttemptId`.** §4.6 sketched
  `provision(exercise) -> Workspace`, but the workspace directory is named after
  the attempt (§8.1), so the alternative is for the provisioner to generate
  identity — which means the `Attempt` learns its own id from its workspace and
  the `IdGenerator` port is injected twice to produce one id.
- **`practice gc --no-dry-run` is refused with an explanation** rather than
  being offered and quietly doing nothing. An orphan is *a workspace with no
  active attempt row* and there is no attempt table until Phase 6; a flag that
  looks like it deletes and does not is worse than one that is not there, because
  the next person to read the output believes the cache was cleared.

One confirmation worth recording. §6.6 reports c2's tree as `0b2626fa` from the
hand-run done before Phase 0. The provisioner reproduces that exact tree, under
a *different* pinned identity — tree hashes do not cover the author or committer,
so it is the one value from that record this code can check independently. The
commit hashes in §6.6 differ from the committed lock file for the same reason,
and the lock file is now the authority. `tests/integration/sandbox/
test_provisioner.py` asserts the tree directly, so the §6.6 record and the
running code are tied together rather than merely consistent.

The pattern across Phase 3 matches the one from the two authoring sessions:
every finding came from running something. The spike that discovered
`shutil.rmtree` failing with `WinError 5` on a read-only git object, and WSL's
`bash.exe` sitting ahead of Git Bash on `PATH`, took fifteen minutes and saved
the two most likely multi-hour debugging sessions in the phase.

**2026-10-01 — phase plans corrected after phase 3.** Writing phase 3's commits
exposed a defect in how §11 was written rather than in any one phase: the commit
lists were *narrative* orders, not dependency orders. Phase 3's opened with
workspace provisioning, which needs the fixture runner it placed fourth. Two of
its test files needed fixtures the list placed two commits later. None of that
was visible until the commits existed and each was checked out and run.

§11 now states the rule — every commit in a list is green on its own — with the
verification loop and the two traps in it: an editable install makes a
`git worktree` run the working tree's source against the commit's tests, and an
untracked file from a later commit survives `git checkout` and contaminates the
run the same way. Both produced failures that were artifacts of the method, and
both were initially mistaken for real ones.

Auditing the remaining phases against the same rule found four more problems,
all of them omissions rather than orderings:

- **Phase 4 cannot ship as listed.** `StartAttempt` saves through the
  `AttemptRepository` port and the SQLite implementation is Phase 6, and nothing
  builds the object graph for the CLI. Phase 4 now adds an in-memory repository
  and `composition.py` — the former not as scaffolding but as the second
  implementation that keeps the port honest under the §13 rule, and the one the
  application tests will use permanently.
- **Phase 5's first and third commits claimed work already done.** The
  `RepoQuery` *port* shipped in Phase 1 with every other protocol, and
  `domain/checks/registry.py` shipped in Phase 2 as the set of legal `assert:`
  names. That phase adds implementations and turns the set into a dispatch
  table; the commit messages now say so.
- **Phase 5 had no commit for the scenario grader.** It went straight from the
  assertions to `SubmitScenario`, which cannot grade without something
  assembling `CheckReport`s into a `Verdict` behind the `Grader` port. Now
  commit 6 of nine.
- **Phase 7 vendored its assets after the templates that reference them**, so
  its first commit would have shipped a layout whose `<script>` 404s — and the
  offline-asset test would not have caught it, because it greps for `http://`
  and a broken local path is not a remote one.

Phase 6's last two commits are also swapped: wiring SQLite in at the root has to
precede the db-aware `gc`, which is the first thing that needs the attempt table
to actually be the attempt table.

Phase 5's *ordering* was fine, which is worth recording because the first
assumption after phase 3 was that it would have the same defect. It does not.
The lesson generalises less than it looked: the failure was specific to a phase
whose foundation module sat at the top of its own list.

**2026-10-01 — Phase 4 built: the kata engine, and the first vertical slice.**
Three sessions budgeted and three spent, but the split was not the expected one:
the grading *logic* was a morning and the pytest *invocation* was most of the
rest. §7 described that invocation in one line, and the line does not work.

Five findings. The first four are all the same finding wearing different hats —
**an isolated subprocess is isolated from things you wanted** — and all four
came out of a fifteen-minute spike run before any module existed, which is now
twice in a row that the spike has been the cheapest part of a phase.

- **`-p practice_report` cannot load the plugin.** §7's invocation fails before
  collection with `No module named 'practice_report'`, because `-I` implies `-P`
  and the workspace is therefore not on `sys.path` when pytest resolves plugin
  arguments. Phase 2 had already spotted the *other* half of this — that
  `from solution import two_sum` would fail for the same reason — and fixing
  only that half would have left the plugin unloadable. The copied-in
  `conftest.py` now registers it through `pytest_plugins`, by which point pytest
  has imported the conftest by path, and inserts the workspace on `sys.path`
  explicitly on the way.
- **pytest colours assertion diffs through a pipe.** The first failure message
  read back from a real run was
  `assert (0, 0) == (1, 2)\n At index 0 diff: \x1b[0m\x1b[94m0...` — ANSI
  escapes, on their way into a `CheckReport` and from there into a verdict panel
  and a SQLite row. `--color=no`. Exactly the problem `color.ui=false` solves
  for git in §6.1, which is the tell: output that will be *stored* has to be
  pinned at the source, not cleaned up at the display.
- **`-I` implies `-E`, so `PYTHONIOENCODING` is not available.** The sandbox
  pins `LC_ALL=C` so git speaks one language; under an ASCII locale, a non-ASCII
  character in an assertion message raises inside pytest's own reporting. The
  only way to pin encoding through `-E` is the command line: `-X utf8`.
- **pytest would have found this project's own `pyproject.toml`.** rootdir
  discovery walks *upwards* from the arguments, so a workspace under any
  ancestor carrying `[tool.pytest.ini_options]` inherits its `addopts` — in this
  project `--cov`, plus `filterwarnings = ["error"]`. A grading run that
  silently obeyed the grader's own config is the kind of thing that works for a
  year and then does not. An empty `pytest.ini` in the workspace plus `-c` pins
  both the config and the rootdir.
- **`TestRecord` and `TestOutcome` broke every test file that imported them.**
  A `Test`-prefixed class in a module pytest is collecting is a test class, and
  one with a constructor is a `PytestCollectionWarning` — which this project's
  `filterwarnings = ["error"]` promotes to a collection *error*. `__test__ =
  False` is the documented opt-out and is preferred here over renaming: a kata's
  hidden suite really is a list of tests, and the domain vocabulary should not
  bend around a prefix convention.

One finding was not about pytest at all, and it is the one worth generalising.
**`ports.py` still declared `provision(exercise)` and had no `attach`** — both
contradicting a deviation this very log recorded when Phase 3 shipped. Nothing
had noticed in a month, because nothing had *called* the provisioner through the
port: the adapter was always used concretely, so the protocol was never checked
against anything. A port with no caller is not checked by mypy either, and
`Protocol`s are structural, so there is no inheritance to complain. The lesson
is narrower than "keep docs in sync": **a port is only verified at the moment a
use case depends on it**, which is an argument for writing the use case in the
same phase as the adapter rather than two phases later.

Three bugs were found by the tests that were written to describe the code, which
is the ordinary case but worth counting: `label_for` indexed into an empty list
for a docstring that was only whitespace; `TestRecord.name` took the segment
after the *last* `::`, which collapses `TestSorting::test_empty` and
`TestParsing::test_empty` into one check id; and a test asserting that a second
submission is refused by the aggregate was wrong about *which* guard fires —
the workspace is disposed on submit, so `attach` returns `None` and the solver
sees `WorkspaceGoneError` long before `Attempt.complete` gets a chance. That
last one had been written to accept either exception, which is how it passed
while describing the wrong mechanism; pinning it to one was the fix.

Six deliberate deviations from the plan as written, all folded back above:

- **`Workspace` grew `run_tool`.** The kata engine needs to run
  `python -m pytest` in the workspace, and a kata's allowlist is empty by
  design, so `run` refuses it — correctly. The alternatives were worse: typing
  `KataGrader.grade` against the concrete `SubprocessWorkspace` breaks the
  `Grader` protocol outright (parameter types are contravariant, so a narrower
  one is not a `Grader`), and exposing the workspace's `Path` and environment on
  the port leaks the filesystem into the domain to do by hand what the adapter
  already does. `run_tool` names the §8.1 trust split on the port instead:
  untrusted input through `run`, engine-authored argv through `run_tool`, the
  same scoped environment and output caps for both.
- **The in-memory `AttemptRepository` stores and returns deep copies.** The
  obvious version keeps the caller's object, which makes `save` nearly a no-op —
  mutate the aggregate afterwards and the change "persists" by accident. Every
  use case would then pass its tests here and lose data against SQLite in Phase
  6, where a row is only what the last `save` wrote. Copying is the whole reason
  this adapter is evidence of anything rather than scaffolding, and two tests
  assert it in both directions.
- **`adapters/kata/grader.py` is a third module** where §10 lists two, and the
  grader takes a `KataRunner` protocol rather than the concrete runner. That
  protocol is what makes the timeout and collection-error branches
  millisecond-long unit tests instead of a ten-second wait each, which is §13's
  two-implementations rule paying out on the day it was written.
- **`application/errors.py` is a fourth module** where §10 lists three. A
  `DomainError` means an aggregate refused an operation; these mean the request
  could not be satisfied — nothing resolves that id, nothing can grade that
  kind, the workspace is gone. Four narrow types rather than one error with a
  code, because every driving adapter maps them to something (an exit status, a
  status code) and a match on a type is checked while a match on a string is
  not.
- **`practice solve` does start *and* submit in one process.** A Phase 4
  constraint rather than a design: the attempt repository is in memory, so an
  attempt cannot outlive the invocation that created it, and shipping
  `practice start` / `practice submit` now would mean a `submit` that can never
  find its attempt. With no `--source`, it grades the exercise's own stub —
  which makes the first run of the command show the hidden suite working, and is
  the same property §9 requires of every kata in the library.
- **`tests/e2e/` opens with the kata half only.** §9 wants one kata and one git
  scenario driven through the CLI; the scenario half needs the Phase 5 engine.
  Two tests, deliberately: an e2e layer that grows becomes the slowest and least
  informative part of the suite, so anything assertable one layer down lives one
  layer down.

**The commit-split check earned its place twice, and then got cheaper.** §11's
rule — every commit in a list is green on its own — was written after Phase 3,
and running it over Phase 4's seven commits found two defects that a green
working tree had hidden completely:

- **Commit 1 imported from commit 2.** Its runner test pulled `check_id_for`
  out of `grader.py`, which lands a commit later, so commit 1 could not collect
  its own tests. The familiar shape, and the fix made the test better as well as
  earlier: a runner test asserting on `TestRecord.name` speaks the runner's own
  vocabulary, and how a name becomes a check id is the grader's business.
- **A 108-character docstring line was broken on every commit from three
  onward, including the tip.** It was introduced while *staging* commit 3, after
  the last full `ruff check` had already passed — so it was not merely missing
  from one commit, it was on `main`. The lesson is duller than the first and
  more generally useful: **a check run before the last edit is a check that did
  not run.** The per-commit loop covers lint and types as well as tests, which
  is the only reason it was found before CI found it.

The check itself then changed shape. Running the whole suite against every
commit costs about four minutes each — half an hour for this phase, repeated
every time the split is adjusted — and a check with that much friction is one
that gets skipped, which is strictly worse than a cheaper check that runs. §11
now describes two tiers: lint, types and that commit's own tests per commit
(seconds), and the full suite with the coverage gate once before a push, which
is what CI runs anyway. **`mypy` turns out to do most of the work**, because the
defect this rule exists to catch — a commit importing something a later commit
adds — is a type error in isolation, named by module and line, with nothing
executed. Both of the defects above would have been caught by the cheap tier.

The phase closed at **699 tests**, with `domain/` and `application/` at **100%**
statement and branch coverage against the 90% gate, and
`tests/content/test_katas.py` now grading every kata's reference and stub —
which shrank `unproven_by_design` from three caveats to two and tripped the
Phase 2 tripwire exactly as designed. What is still unproven is scenario
grading, which is Phase 5 and is the only thing the list still admits to.

**2026-10-01 — Phase 5 built: the git scenario engine.** Nine sessions budgeted,
nine commits plus the spike and the overdue ADR. The longest phase in the plan,
and the one carrying the widest error bars, came in on its revised estimate — the
earlier five-session figure would not have.

**The headline result is that the implementation agrees with the hand-run oracle,
row for row.** §6.6 recorded eleven rows across two scenarios, executed by hand
against real git before Phase 0 began. The engine reproduces every one of them,
including `naive-reset-force` failing only `history-preserved` while tripping the
`no-force-push` advisory. The vocabulary designed on paper, validated by hand and
then implemented needed **no changes** — which is the single most reassuring thing
to come out of the phase, because it is the thing that could not be checked until
now.

**The port was not complete, and building the engine found three gaps.** Phase 1
shipped every protocol in `domain/ports.py` and the phase plan said so in as many
words: "the **port** is already there … so this phase adds implementations, not
the interface." Three methods were missing, and each was invisible until an
assertion needed it:

- **`RepoQuery.head_ref()`.** `head_detached` cannot be answered without it.
  `rev_parse("HEAD")` returns a hash whether HEAD is attached or not, and "no
  branch points at this commit" is a different question with a different answer —
  a detached HEAD sitting exactly on a branch tip is still detached, which is the
  state `naive-detached-checkout.cmds` ends in and the whole reason that
  counter-example exists.
- **`RepoQuery.worktree_file()`.** `file_exists` and `file_matches` are only
  distinct from `file_at_ref_matches` if they read the *working tree*, and without
  it nothing could grade a state that has not been committed — which is exactly
  what a merge-conflict exercise ends in (§15, question 1).
- **`Workspace.aliases()` and `.snapshot()`.** A `RepoQuery` is built *over* a
  `Workspace` and `Grader.grade` is handed the port, so the alias map and the ref
  snapshot have to be reachable through it. They live outside the repository on
  purpose (§6.1), so `read_file` — which confines itself to the repository —
  cannot reach them.

The pattern is worth naming, because it will recur: **a port designed from the
consumer's description is a port with holes in it.** All three gaps were in
questions nobody had written down as questions, not in types anyone got wrong.

**Two Windows findings, both from running it.** A literal NUL in a `--format`
argument is rejected by `CreateProcess` outright, as a `ValueError: embedded null
character` raised from inside `subprocess` before git starts — so the separator is
asked for as git's own `%x00` escape, which expands in git's *output*. And
porcelain v2 puts a rename's path one field later than an ordinary change's, which
fails silently: the path parses as `R100 renamed.py` and every assertion about it
fails in a way that looks like the solver's fault.

**The conformance suite earned its keep on its first run.** `FakeRepoQuery` is
loaded from a real repository's raw data and then both implementations are asked
the questions neither was given the answer to — `rev_parse` over fourteen
spellings, `tree_sha`, `subject`, `is_ancestor` over every ordered pair of
commits, reachability, which commits are merges. 675 comparisons across two
scenarios in six states each. It immediately caught the fake being loaded from
`log --all`, which walks refs — and the entire premise of `recover-a-lost-commit`
is two commits no ref points at any more. `rev_parse("HEAD@{3}")` agreed, because
a reflog entry carries its own hash, and then the fake had no commit object to
answer `tree_sha` or `subject` from. Eight failures in one state of one scenario,
and exactly the class of gap a fake quietly carries when nothing compares it to
the real thing.

**The graded replay found a content defect, which is what it is for.**
`recover-a-lost-commit` declared one `expect_failures` entry per counter-example
where its own §6.6 table records three, two and three — and its yaml comment said
"others may fail too", contradicting the `exactly` this plan specifies twice. The
plan is right and the content was under-declared, so the content is fixed. Worth
being clear about *why* exactly rather than at least, since both catch the rot the
original rationale describes: equality makes `expect_failures` a complete,
reviewable statement of what a wrong answer gets wrong, and its cost — adding a
required check breaks every counter-example that happens to fail it — is the
feature.

**Two things the plan's §6.3 placement got wrong, both small.**
`no_conflict_markers` is filed under "worktree and index" and lives in `trees.py`:
it reads file content rather than status, so it shares the blob read with
`file_matches` and would share nothing with the status assertions. And §10's
`adapters/git/graph.py` does not exist — ancestry is `git merge-base
--is-ancestor`, and the only code that walks a commit graph by hand is the test
fake. A module to hold one function nothing calls is the abstraction §13 says to
delete rather than carry.

**One defect in Phase 4's code, surfaced by Phase 5's tests.** Submission disposes
of the workspace, so a second submission — or a stale browser tab sending one more
command — reached `attach`, found nothing, and was told the workspace was gone and
to *abandon the attempt and start again*, about an attempt that had just been
graded successfully. `Attempt.complete` refuses the second call with the right
message and was simply never reached. Phase 4 pinned the old behaviour in a test
whose docstring said both refusals were correct; the ordering it pinned was right
and what that ordering produced was not. All three use cases check the status
themselves now.

**The shape that carried the phase: assertions return a result, not a report.**
Each of the 22 says what it expected, what it found, and whether those agree — and
nothing about the exercise. One dispatcher applies `not:`, carries the author's
label and severity across, and turns a malformed `with:` mapping into a failing
check rather than a traceback. §6.3 made `not:` a uniform modifier instead of six
paired opposites; a function that built its own report would have had to invert its
own verdict *and* rewrite its own `expected` string, which is 22 chances to get it
wrong and one of them reporting a failure as a pass.

**The commit split found two red commits, and the loop pointed at the wrong ones.**
Commits 7, 8 and 9 all failed in isolation on the same three tests. The cause was
one commit: commit 7 emptied the kind registry's `_PENDING` map and registered the
scenario grader, which changed a refusal message that
`tests/integration/test_cli_solve.py` asserted on, and changed
`unproven_by_design`'s caveats in commit 8 the same way. Neither commit touched
`tests/integration/`, so the cheap tier — whose `paths` come from the test
directories a commit *touches* — ran neither of those files and reported both
commits clean. The blame landed on commits 8 and 9, which did touch them.

`mypy` could not help, because the break was a string assertion rather than a type.
Attributing it took one pass of the failing files over the whole range, which is
seconds per commit; §11 now carries that as the third caveat on the loop, with the
loop to use. All three commits were amended so each is green on its own, and the
test that moved changed **three times** across the phase — naming Phase 5, then the
kata path having no stub, then the flag the exercise takes — because the behaviour
it pins genuinely changed three times. That history is left visible rather than
flattened.

The general lesson is the same one Phase 4 recorded in a different key: **a check
scoped to what a commit touched cannot see what a commit broke.** The cheap tier is
a bisectability check for collection and type errors and an attribution *hint* for
anything else, and the pre-push tier is still the one that decides.

The phase closed at **1,669 tests** — 970 more than Phase 4, two thirds of them the
conformance suite's comparisons — with `domain/` and `application/` back at **100%**
statement and branch coverage against the 90% gate. The §9 content suite is
complete, and `unproven_by_design` is down from two phase-shaped caveats to two
permanent ones: this command runs nothing by design, and nothing can tell you
whether a check's prose is true of the assertion it is attached to. **Every caveat
the tool has ever printed has now been retired rather than deferred**, which is the
first time that has been true.


**2026-10-02 — Phase 6 built: persistence, and the attempt lifecycle completed.**
Three sessions budgeted, six commits. The phase that was supposed to be a test of
the previous five, and was.

**The swap really was one line per repository.** §11 set commit 4 up as the check:
*"one line per repository if the ports have been respected — and if it is not, that
is the finding."* `composition.py` changed; no use case, no grader and no CLI
command did, because none of them had ever held anything but an `AttemptRepository`.
That is the only evidence the ports of Phases 1–5 were real rather than decorative,
and it is worth recording that the evidence arrived five phases after the decision.

**Four findings, in descending order of how much they changed.**

- **Reconstitution is not replay, and the aggregate needed a door for it.** The
  elegant-looking way to rebuild an `Attempt` is through its own public API —
  construct, `record_command` per stored command, `complete`. It is wrong twice. It
  re-checks *today's* policy against *last month's* attempt, so an exercise edited
  down from twenty-five commands to ten would make old attempts unloadable; and it
  re-runs invariants that were already satisfied, so the aggregate could refuse to
  load a row it had itself produced. `Attempt.restore` bypasses the behavioural
  guards and enforces only what a *row* can be wrong about: naive or out-of-order
  timestamps, and the three pairings between status, finish time and verdict. The
  same rules appear again as CHECK constraints in the schema, which is the
  deliberate duplication `Attempt` and the sandbox already document, with a third
  job added — the aggregate refuses to *reach* an impossible state, the schema
  refuses to *store* one, `restore` refuses to *load* one. Recorded in ADR 0006,
  because it is the one place persistence reached into the domain.

- **`practice start` was missing from the commit list, and the phase does not work
  without it.** Writing `attempts`, `resume`, `submit` and `abandon` made it
  obvious: `solve` starts and submits in one process, so nothing in the shipped CLI
  ever leaves an attempt open, and all four new commands had no reachable state to
  act on. The exit criterion — *attempts survive a restart and can be resumed* —
  was literally untypeable. §11's rule about checking a commit list against the
  actual imports has a sibling: **check it against the states the commands can
  reach.** A list can be in dependency order and still describe a product with no
  way into the state it adds.

- **Two SQLite behaviours that reading would not have settled.** `PRAGMA
  journal_mode=WAL` cannot execute inside a transaction, so `autocommit=False` —
  which opens one before the first statement — makes the WAL pragma fail on a fresh
  database. The connection is therefore opened in full autocommit and the
  transaction is `BEGIN IMMEDIATE`/`COMMIT` issued as SQL. The second: inside an
  open transaction, `executescript` does **not** commit it, so each migration is
  atomic and a failing one leaves no DDL behind — but that differs between the
  driver's two transaction modes, which is why there is a test pinning it rather
  than a comment asserting it.

- **The orphan rule has to be decided on the directory name.** PLAN.md §8.1 defines
  an orphan as a workspace with no corresponding `active` attempt row, and the
  obvious join is on the `attempt_id` in the workspace's own metadata. That gets
  the most interesting case backwards. The leftover most worth collecting is an
  interrupted provision, whose metadata was never written: it has no `attempt_id`,
  so a metadata join classifies it as belonging to nothing *and* cannot address it
  for deletion. Deciding on the directory name — which *is* the attempt's short id
  — makes the undescribed workspace and the completed attempt's workspace the same
  case, which is what they are. `SandboxProvisioner.discard` is keyed the same way,
  and that turned out to matter for a second reason: `AbandonAttempt` cannot
  `attach` to dispose of a workspace when the exercise has been deleted from the
  library, and that is precisely the case abandoning exists for.

**Two things were added beyond the plan's list, both small and both argued for in
the commits.** `InMemoryReviewRepository`, because `ReviewRepository` had been
declared since Phase 1 with *no* implementation, which under §13 is the weakest
position a port can be in; and a second architecture rule, that only
`adapters/persistence` may import `sqlite3`, in the same shape as the Phase 3 rule
about `subprocess` and with the same paired test that the package really does
import it.

**One thing was deliberately not built.** A review *log* — every grade ever given
with the interval it produced — is what would let Phase 9's scheduler be evaluated
against its own history rather than only property-tested. It is also a table
nothing in the MVP reads, so a card is replaced and the `reps`/`lapses` counters
are what survives. The asymmetry to remember if that is revisited: the counters are
derivable from a log and the log is not derivable from the counters.

**The per-commit tier earned its keep again, and its known caveat bit again.** On
the useful side: commit 5 renamed `FakeProvisioner.workspaces` from a dict to the
port's own method, and `mypy` located every one of the nine call sites across three
test files by name and line with nothing executed — tedious, not risky, and exactly
where a type checker is worth most. On the other side, the Phase 5 caveat repeated
itself almost exactly. Commit 5 changed `gc --no-dry-run` from a refusal into a
collection; two tests in `tests/integration/test_cli_sandbox.py` asserted the old
refusal, including one matching the string `"phase 6"`; and commit 5 touches no file
in that directory, so the cheap tier never ran them. **The pre-push run is what
found it, which is the division of labour §11 describes working as described** —
but it is now the second phase in a row where the thing the cheap tier missed was a
*string* assertion in a directory the commit did not touch, and that is a pattern
rather than an accident. The commit was amended so it is green on its own.

The phase closed at **1,862 tests** — 193 more than Phase 5 — with `domain/` and
`application/` at **100%** statement and branch coverage against the 90% gate, on
1,315 statements and 250 branches. Four phases were
blocked on this one: `practice gc` could not define an orphan, §8.1's
resume-or-abandon promise could not be kept, Phase 8's workbench needs an attempt
to survive an HTTP request, and Phase 9's spaced repetition is meaningless if
nothing is remembered between runs. None of them is blocked now.
