# swe-practice — Implementation Plan

An offline practice environment for the two things entry-level engineers are
actually tested on: **data-structure problem solving** and **operational
competence with git**. Local web app, no network, no accounts, no CDN.

> **Status:** planning. Nothing implemented yet.
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

### 4.1 Value objects (`domain/ids.py`, `domain/exercise.py`)

```python
ExerciseId   # slug, e.g. "git/revert-a-pushed-commit"
AttemptId    # uuid4
ExerciseKind = Enum("KATA", "GIT_SCENARIO")        # extensible
Difficulty   = Enum("INTRO", "EASY", "MEDIUM", "HARD")
Tag          # NewType(str): "two-pointers", "history-rewrite", ...
Severity     = Enum("REQUIRED", "ADVISORY")
Grade        = Enum("AGAIN", "HARD", "GOOD", "EASY")
Outcome      = Enum("PASS", "PASS_WITH_ADVISORIES", "FAIL")
```

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
    events: list[AttemptEvent]      # CommandRun | HintRevealed | SolutionSaved
    hints_revealed: int
    declared_complexity: str | None # self-reported Big-O, katas only
    verdict: Verdict | None

    def record_command(self, cmd, result) -> None: ...
    def reveal_next_hint(self) -> Hint: ...
    def complete(self, verdict: Verdict) -> None: ...
    def elapsed(self, now) -> timedelta: ...
```

Invariants it enforces (each with a unit test): cannot record events after
completion; cannot complete twice; cannot reveal more hints than the policy
holds; command count cannot exceed `policy.max_commands`.

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
| `ContentRepository` | `list_exercises(filter)`, `get(id)` |
| `AttemptRepository` | `save`, `get`, `history_for(exercise_id)` |
| `ReviewRepository` | `get_card`, `save_card`, `due_on(date)` |
| `SandboxProvisioner` | `provision(exercise) -> Workspace` |
| `Workspace` | `run(argv, timeout)`, `read_file`, `write_file`, `dispose` |
| `RepoQuery` | read-only git interrogation — see §6.2 |
| `Grader` | `grade(exercise, workspace, attempt) -> Verdict` |
| `Scheduler` | `next_card(card, grade, today) -> ReviewCard` |
| `Clock` | `now()`, `today()` |
| `IdGenerator` | `new_attempt_id()` |

`Clock` and `IdGenerator` look like over-engineering until the first test that
needs a deterministic due date or a stable snapshot. Inject them from day one;
retrofitting them is miserable.

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
references:
  leetcode: 1        # pointer only; no problem text copied
```

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

Every one of the ~25 assert types gets full unit coverage against the fake, in
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
and ~25 asserts down to 19. The `label:` field carries the human sentence, so
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
   `conftest.py`, and a **copy of** `practice_report.py`. The plugin file is
   copied in rather than imported from the app package, because `-p` takes a
   module name and the module has to be importable from the workspace — copying
   it is what lets the subprocess stay isolated.
2. Run with `sys.executable` (the app's own interpreter) in **isolated mode**:
   `python -I -m pytest tests.py -p practice_report --report-out report.json`.
   `-I` suppresses user site-packages and `PYTHONPATH`, so a stray environment
   variable on your machine cannot change how a kata grades.
3. The plugin writes one JSON record per test (nodeid, outcome, message,
   duration). **Written ourselves rather than pulling in `pytest-json-report`**
   — it is ~40 lines, removes a dependency, and produces exactly the shape we
   want.
4. Each test maps to one `CheckReport`, using the test's docstring as the
   human-readable `label` when present.
5. Timeouts are enforced at the subprocess level, not via `pytest-timeout`.

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
   the check functions live in `domain/checks/` (§6.2), the ~25 assertions fall
   inside this gate rather than outside it — which was the whole point of
   putting them there.
2. **Architecture test** — AST-walks `domain/` and `application/`, fails on any
   import from `adapters/` or `interface/`. See §3.
3. **Check-engine tests** — all ~25 assert types against `FakeRepoQuery`. No git
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
│   │   ├── ports.py  errors.py
│   │   ├── checks/          # registry + ~25 PURE assert functions (§6.2)
│   │   │   ├── registry.py  refs.py  trees.py  worktree.py
│   │   │   └── recovery.py  process.py
│   │   └── scheduling/sm2.py
│   ├── application/
│   │   ├── dto.py  registry.py
│   │   └── use_cases/*.py
│   ├── adapters/
│   │   ├── content/{schema,loader,filesystem}.py
│   │   ├── persistence/sqlite/{connection,migrations/,attempts,reviews,mappers}.py
│   │   ├── sandbox/{workspace,provisioner,command_policy,virtual_commands,env}.py
│   │   ├── git/{repo_query,fixture_runner,graph}.py
│   │   ├── kata/{pytest_runner,report_plugin}.py
│   │   └── clock.py  ids.py
│   ├── interface/
│   │   ├── web/{app,security}.py + routes/ templates/ static/
│   │   └── cli/main.py
│   ├── composition.py
│   └── config.py
├── content/
│   ├── _lib/fixture_lib.sh          # commit_as, mkremote, publish, write_file
│   ├── fixtures.lock                # cross-platform SHA verification
│   └── {katas,git}/…
├── tests/{unit,integration,content,web,e2e,fakes}/
└── tools/vendor_assets.py
```

---

## 11. Phases

Sequenced so every phase ends with something runnable. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/) — worth doing
because it makes the git history itself part of the portfolio.

**Effort** is in *sessions* ≈ 2–3 focused hours, at entry-level pace.
**Phases 0–9 (the MVP) total ~40 sessions, so on the order of 100 focused
hours.** That is a real project, not a weekend. Phase 11 roughly doubles it.

Phases 3 and 5 carry the widest error bars — they are the ones with genuine
unknowns (cross-platform subprocess behaviour, and ~25 assertions against two
`RepoQuery` implementations). If a phase is going to run over, it is one of
those two.

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

**Commits**
1. `feat(content): add pydantic schema for exercise files`
2. `feat(content): add filesystem content repository`
3. `feat(cli): add practice validate command`
4. `content: add first kata and two git scenarios`

**Exit:** `practice validate` passes on all three exercises and fails with a
clear, located message on a deliberately broken file.

**Sequencing note:** the *schema* half of the content integrity suite lands
here, but the *replay* half — proving `solution.cmds` passes and `naive.cmds`
fails — needs the sandbox (Phase 3) and `RunScenarioCommand` (Phase 5). Until
then the git scenarios are structurally validated but not yet proven solvable.
Don't mistake green here for content that works.

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
- Workspace lifecycle: explicit `dispose()`, plus a filesystem-only
  `practice gc --dry-run`. The DB-aware orphan definition and resume-or-abandon
  from §8.1 need the attempt table, so they land in Phase 6 — until then `gc`
  only ever reports, never deletes.

**Commits**
1. `feat(sandbox): add workspace provisioning with a scoped git environment`
2. `feat(sandbox): pin git config for cross-platform reproducibility`
3. `feat(sandbox): add command policy and virtual file commands`
4. `feat(sandbox): add fixture runner with deterministic shas and aliases`
5. `feat(sandbox): add attempt lifecycle with resume and safe gc`
6. `test(sandbox): add cross-platform integration tests`

**Exit:** the same fixture produces **byte-identical commit SHAs** on Windows
and Linux CI. Prove it by having both jobs write their SHAs and compare against
a committed `content/fixtures.lock`, **not** by hard-coding a literal SHA in a
test — that way a git upgrade that changes hashing shows up as an explicit
lockfile diff you review, rather than a mystery red build.

---

### Phase 4 — Kata engine, first vertical slice · 3 sessions

First end-to-end value. You can solve a kata after this phase.

- pytest report plugin + subprocess runner with timeouts
- `KataGrader` mapping test results to `CheckReport`s
- `StartAttempt`, `SubmitSolution` use cases
- CLI: `practice solve katas/two-sum`

**Commits**
1. `feat(kata): add pytest report plugin and sandboxed runner`
2. `feat(kata): add grader mapping test results to check reports`
3. `feat(app): add StartAttempt and SubmitSolution use cases`
4. `feat(cli): solve a kata end to end from the terminal`

**Exit:** a kata solved from the terminal, correctly passing and correctly
failing, with the content test proving stub fails and reference passes.

---

### Phase 5 — Git scenario engine · 9 sessions

The heart of the project, and by a wide margin the longest phase. Two
`RepoQuery` implementations, ~25 assertions with tests, a conformance suite and
two use cases is simply a lot of surface — the earlier 5-session estimate was
wishful.

- `RepoQuery` port, `GitRepoQuery` adapter, `FakeRepoQuery` fake
- Conformance suite proving the two implementations agree
- Check registry plus ref and tree assertions (in `domain/checks/`, §6.2)
- Worktree, index, stash, reflog assertions
- Advisory/process assertions over the attempt event log
- `RunScenarioCommand`, `SubmitScenario` use cases
- **Solution replay**: run `solution.cmds` / `naive.cmds` through the real
  policy, completing the content integrity suite deferred from Phase 2
- CLI scenario driver
- **Spike:** whether `rebase -i` is drivable with a non-interactive
  `GIT_SEQUENCE_EDITOR` stand-in. Decide this *before* promising `rebase -i`
  content in Phase 11.

**Commits**
1. `feat(git): add RepoQuery port with a git adapter and in-memory fake`
2. `test(git): add conformance suite for RepoQuery implementations`
3. `feat(checks): add registry with ref and tree assertions`
4. `feat(checks): add worktree, stash and reflog assertions`
5. `feat(checks): add advisory assertions over the command log`
6. `feat(app): add RunScenarioCommand and SubmitScenario use cases`
7. `feat(content): replay reference solutions through the command policy`
8. `feat(cli): solve a git scenario end to end from the terminal`

**Exit:** the revert-a-pushed-commit scenario passes via `revert`, and
`reset --hard` fails the `history-preserved` check with a useful explanation.
That contrast **is** the product working.

---

### Phase 6 — Persistence · 3 sessions

- SQLite connection (WAL, `foreign_keys=ON`), numbered SQL migration runner
- `SqliteAttemptRepository` with explicit row↔domain mappers
- `SqliteReviewRepository`
- **Attempt lifecycle completed:** resume-or-abandon on startup, and `gc`
  promoted from dry-run to real deletion now that "orphan" can be defined
  against the attempt table (§8.1)
- Wire everything through `composition.py`

**Commits**
1. `feat(db): add sqlite connection and migration runner`
2. `feat(db): add attempt repository with explicit mappers`
3. `feat(db): add review card repository`
4. `feat(app): add attempt resume and db-aware workspace gc`
5. `refactor: wire repositories through the composition root`

**Exit:** attempts survive a restart and can be resumed; migrations apply
cleanly from empty and are idempotent; `gc` provably never deletes the
workspace of an active attempt.

---

### Phase 7 — Web shell and kata workbench · 4 sessions

- FastAPI app, base templates, loopback assertion, cross-origin middleware
- Vendored htmx + CodeMirror with a hash-pinned fetch script
- `/browse` and the kata workbench
- HTMX submit flow with a verdict panel

**Commits**
1. `feat(web): add FastAPI app, base templates and loopback guard`
2. `chore(web): vendor htmx and codemirror for offline use`
3. `feat(web): add browse and kata workbench pages`
4. `feat(web): add htmx submit flow with verdict panel`

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

| ADR | Decision |
|---|---|
| 0001 | Record architecture decisions |
| 0002 | Ports and adapters, with the boundary enforced by a test |
| 0003 | Grade git exercises by repo state, not command text |
| 0004 | Content as declarative data, validated by schema |
| 0005 | Sandbox via temp dirs and subprocess, not containers |
| 0006 | SQLite without an ORM |
| 0007 | HTMX over a single-page app |
| 0008 | SM-2 first, FSRS behind a port |
| 0009 | Ship our own prompts; never redistribute problem text |
| 0010 | CodeMirror 5 over 6, to avoid an npm build step |
| 0011 | Reference solutions are command lists, not shell scripts |

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
  it twice (real git, in-memory fake), unit-test all 25 assertions against the
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
2. **Interactive rebase** needs `GIT_SEQUENCE_EDITOR`, which §8.1 pins to
   `false` so nothing hangs. Driving it non-interactively means swapping in a
   stand-in that applies a scripted todo-list. Spiked in Phase 5, explicitly
   *before* any `rebase -i` content is promised in Phase 11.
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
  a universal modifier and deleting all six twins — 25 asserts down to 19, and
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
