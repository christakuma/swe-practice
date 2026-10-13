# swe-practice — Implementation Plan

An offline practice environment for the two things entry-level engineers are
actually tested on: **data-structure problem solving** and **operational
competence with git**. Local web app, no network, no accounts, no CDN.

> **Status:** **v1.0.0, seven stretch items taken — Phases 13 through 19 — and
> Phases 20 and 21, the changes that came from a user.**
> Phase 21 is the newest: every kata now states its constraints and shows
> examples that are *run against its reference*
> ([ADR 0027](adr/0027-examples-are-source-run-against-the-reference.md)), on a
> tab of their own; and a problem can carry **variants** — the interviewer's
> follow-up — that a solver picks or draws at random
> ([ADR 0028](adr/0028-a-variant-is-a-whole-exercise-offered-under-its-base.md)).
> Every one of the eighty-three katas has one.
> Phases 0–10 built the engine, Phase 11 filled it with 54 exercises, and Phase
> 12 is the front door and the portfolio artifacts: `uv sync && uv run practice
> up` is the whole of getting started, and it refuses with an instruction rather
> than serving a tool that breaks twenty minutes later
> ([ADR 0017](adr/0017-a-front-door-separate-from-the-server.md)). The README
> carries a hand-written architecture diagram and a demo that is *generated from
> real captured output* rather than recorded
> ([ADR 0016](adr/0016-a-generated-demo-not-a-recorded-one.md)), and
> [the postmortem](postmortem.md) is the honest version of what it cost.
>
> **Phase 13 is stretch, by appetite, and the first item taken is FSRS** — not
> because a second scheduling algorithm is the most valuable thing in §11's menu,
> but because it was the only one with a *prediction* attached.
> [ADR 0008](adr/0008-sm2-first-with-fsrs-behind-a-port.md) deferred FSRS in
> Phase 9 and wrote down in advance what the swap would cost: one line in
> `composition.py`, and a migration that adds columns rather than reusing SM-2's.
> **Both halves held** — twelve files under `src/`, and not one of them a use
> case, a grader or a route: the two that are not `domain/scheduling/`,
> `composition.py` or the interface are the SQLite mapper and the review
> repository, each gaining the two column names, which is the migration showing
> up where it has to. `PRACTICE_SCHEDULER` now selects between them
> ([ADR 0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)). What
> the prediction missed is that one line is not shipping: a scheduler nobody can
> select is written rather than shipped, so the real cost was a registry, a config
> question, a preflight step and a template branch, all four of them in the
> interface and at the root.
>
> **And three things only a second implementation could find.** One of §9.7's
> four scheduler properties turns out to be SM-2's policy rather than a law —
> *"`AGAIN` always resets to one day or less"*, which FSRS does not and should not
> do. §9.7's interval clamp is a property of **whole-day intervals**, not of
> SM-2's arithmetic: FSRS stalls too, from an unrelated cause, and needs the same
> `max(previous + 1, ...)`. And the schedule panel had been printing an ease
> factor that FSRS never moves — present, correctly formatted and meaningless, so
> no fragment assertion could have caught it. The default stays SM-2, for the
> reason ADR 0008 already gave: FSRS without fitted parameters is FSRS without the
> thing that makes it better, and this tool still keeps no review log.
>
> **Phase 14 took the second item with a prediction attached: a third exercise
> kind.** `domain/exercise.py` had claimed since Phase 1 that adding one means
> "adding a spec and a registry entry instead of re-cutting a class hierarchy",
> and SQL drills are what graded it
> ([ADR 0019](adr/0019-sql-drills-as-a-third-exercise-kind.md)). A drill seeds a
> SQLite database from a `seed.sql` the solver is *meant* to read, runs their
> answer in memory, and grades the rows it returned **and the state it left the
> database in** — which is the core bet applied to a second domain, and only a
> real claim for the statements that return nothing at all. Ten pure assertions
> over a `DrillQuery` port, in three families: what came back, what the database
> holds, and — the one this kind is worth having for — what SQLite's own query
> plan says about how hard it worked.
>
> **The inheritance half of the prediction held exactly and the other half did
> not, which was the more useful outcome.** No port widened, no use case
> rewired, `build_services` unchanged, `build_graders` three lines longer. What
> changed is five call sites that had learnt to read `isinstance(spec,
> KataSpec)` as *has a file to edit* — true for exactly as long as there were
> two kinds. **A prediction about the cost of a third case cannot be made from
> two cases**, because the thing that costs is the conflation you cannot see
> yet. `editable_source` names the question once, so a fourth kind pays none of
> it again.
>
> **Five more findings, and the two worth the banner.** `_PENDING` — the mapping
> kept empty since Phase 5 for a kind that exists before its grader — turned out
> to be *unreachable by construction*, because `test_every_exercise_kind_has_a
> _grader` forbids that state; it is deleted under §13's rule, and the commit
> list is five rather than seven because the kind had to land with its engine.
> And §15 Q3's claim that a second language costs "one line in `vendor.py` and
> nothing else" was **nearly** right: the line was, but `workbench.html` had the
> Python mode file hardcoded, so a drill would have degraded to a plain textarea
> with no error anywhere. Nothing could have caught it, because the mode *name*
> was already coming from the spec and already tested.
>
> **The library is the product: 115 exercises — 24 git scenarios, 83 katas and 8
> SQL drills, every one of them graded.** Phase 11 built 54 of them and Phase 17
> added the 53 that fill the Blind 75 gaps; the engine has not changed to hold
> them. Phase 11 is the content that makes the engine worth opening, and its exit bar was never "they load" — `uv run pytest
> -m content` replays every reference solution through the real use cases, holds
> 52 scenario counter-examples and 16 drill counter-examples to failing
> **exactly** the checks they declare, grades every kata's and every drill's stub
> to prove the suite rejects it, and pins all 24 fixtures to
> `content/fixtures.lock` on both platforms. Phases 0–9 are a complete product:
> the core bet works, an attempt survives the process that started it, the two
> exercise kinds that existed then are solved in a browser, and the tool now
> answers *what should I practise today?* instead of leaving it to you. A git
> scenario is graded end to end — `practice solve git/revert-a-pushed-commit
> --reference` passes, and the same exercise replayed with `reset --hard` fails
> `history-preserved` while passing `content-restored`, because the trees are
> identical and the ancestry is not. Underneath: 20 pure assertions over a
> read-only port implemented twice and proved to agree, a content suite that
> grades every reference solution and holds every counter-example to the checks
> it declares, an attempt that lives in SQLite across four processes sharing one
> repository and one budget, and an HTMX app that serves every byte off the disk
> and refuses any request it cannot prove came from its own page. **Phase 9
> closes the loop**: SM-2 behind the `Scheduler` port
> ([ADR 0008](adr/0008-sm2-first-with-fsrs-behind-a-port.md)), property-tested on
> the four invariants §9.7 states; a grade the tool *suggests*
> from the verdict, the hints revealed and the time taken, which the solver
> presses or overrides; a due queue that offers the whole library before anything
> is scheduled and drops an exercise the moment it is; and a dashboard and a
> `/progress` page — streak, weakest tags, mastery by tag, activity window —
> drawn as hand-rolled inline SVG with no dependency.
>
> **Phase 10 lets you solve a kata without the browser's editor at all.** The
> stub the provisioner already copies into the workspace *is* the working copy,
> so own-editor mode needed a path rather than a scaffold: `practice start` now
> prints it, and the workbench opens your editor on it through an
> `EditorLauncher` port that reports a missing editor instead of raising. A
> `watchfiles` watcher behind a `FileWatcher` port notices every save and an SSE
> endpoint streams back the same verdict fragment a submission would have
> rendered — as a **preview that persists nothing**
> ([ADR 0013](adr/0013-grade-on-save-is-a-preview.md)): the attempt is handed
> the file's contents in memory, graded, and never saved, so the event log stays
> a record of what the solver did rather than of what they typed.
>
> **Phase 11 is the library, and three findings the library forced.** Every
> prompt, hint, note and test is written here rather than borrowed
> ([ADR 0009](adr/0009-ship-our-own-prompts.md)), which is what lets a prompt
> state exactly what the grader checks. The content then found three gaps in the
> engine it was written against: a conflict scenario's answer *begins* with a
> command that exits 1, so a reference solution can now declare how many of its
> commands fail — counted, not flagged, so a typo in the same file is still
> caught; `@{u}` is a git revision and the content suite had been treating any
> `@`-prefixed parameter as a fixture alias; and the two assertions Phase 5
> shipped flagged as unproven went unused across all 24 scenarios, so they are
> **deleted** and the vocabulary is twenty. The order the library is offered in
> is now a hand-written manifest that `validate` holds to covering it exactly
> ([ADR 0014](adr/0014-a-hand-ordered-curriculum-manifest.md)) — it had been
> `sorted(ExerciseId)`, which put the hardest kata fifth.
>
> **Phase 12 is the two minutes between cloning this and solving something.**
> `practice up` asks the four questions a fresh machine fails — is git
> resolvable, does the content root list exercises, can the cache directory be
> created, can every migration be applied — while there is still a terminal to
> answer in, and reports all of their problems in one pass rather than one per
> run. It exists as a second command rather than as a change to `serve` because
> `serve` starting a server *and nothing else* is a property the web suite
> depends on. The phase also found the one thing the test suite could not: an em
> dash in the first line a stranger reads arrives as a replacement character on
> a fresh Windows console.
>
> **Phase 15 took the third item, and it is the first whose prediction is in the
> menu itself.** §11's table said interview mode touches *application-layer
> policy*; Phase 14's log called it the cheapest item on the menu. Two of its
> three clauses are exactly that, and one of them cost **nothing at all** — an
> empty `hints` tuple makes `Attempt.reveal_next_hint` refuse on the first
> request and the workbench already drew its panel on `hint_count`, which is
> §4.3's claim about `AttemptPolicy` paying off as stated. The clock needed no
> new rule either: `suggest_grade` has compared elapsed time against
> `estimated_minutes` since Phase 9, and an interview's deadline *is*
> `estimated_minutes`, so a timed attempt was already graded from its end state.
>
> **The third clause could not be built, and that is the phase's value.** "No
> test peeking" asks for containment, and §8.1 ruled containment out in Phase 3:
> a kata's `tests.py` is in the workspace because `pytest` must run it from
> there, and the solver owns the machine. So what ships is the weaker and honest
> thing — `AttemptPolicy.reveals_workspace` withdraws every affordance the tool
> provides for peeking and says that is what it did
> ([ADR 0020](adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md)).
> The record spends its longest alternative rejecting the stronger version,
> because it would widen `SandboxProvisioner.provision` to buy a boundary that
> still would not be one.
>
> **And the Phase 13 ease-factor finding repeated in a second place.** The review
> panel printed "passed clean, inside the estimate, no hints" for an attempt that
> was never offered one — present, correctly formatted and meaningless, exactly as
> invisible to a fragment assertion as the ease factor was. It had also always
> been wrong for an exercise authored without hints, latent only because the
> content suite requires every shipped exercise to carry some.
>
> **Phase 16 took the fourth item, and it is the first the project nominated for
> itself.** Phase 15's log closed by calling exportable content packs "the
> cheapest item on the menu and the only one that would give a port its second
> real implementation", and both halves held: `ContentRepository` was the last
> port taking §13's two-implementation rule on credit, and
> `PackContentRepository` reads a library out of a zip without extracting it
> ([ADR 0021](adr/0021-content-packs-install-rather-than-mount.md)). The 62
> exercises are now a 360 KB file that `practice pack --check` verifies and
> `--install` lays out as a content root, and a *subset* is a library in its own
> right — which took deriving `curriculum.yaml` and `fixtures.lock` rather than
> copying them, because a pack of part of a library that carried them verbatim
> installs to a root that fails both of the commands CI runs over `content/`.
>
> **The menu's `Touches` column said "a content repository adapter", and the
> adapter was exactly that cheap while the feature was not.**
> `SandboxProvisioner` is constructed with a `content_root: Path` and resolves
> `content_root / exercise_id` itself, so a fixture, a stub, a `tests.py` and a
> `seed.sql` reach a workspace by being copied from a directory and **never
> through the port.** The library has two readers and only one is behind a
> protocol: the port is the *catalogue*, and a pack-backed library can therefore
> be browsed and not solved. ADR 0021 rejects the widened port for a reason that
> only emerged while writing it down — the files have to be written to a
> directory either way, so carrying bytes on the port moves the extraction inside
> `provision` and makes it happen per attempt rather than once per install.
>
> **And the number that did not move is the phase in one line.** 100% coverage
> over a gated surface of 2,419 statements and 496 branches — *exactly* Phase
> 15's figures, because a pack format, a second repository and a CLI command are
> an adapter, an adapter and an interface, and the only thing this phase put in
> `domain/` is a docstring. The first phase to ship a feature and add nothing at
> all inside the gate.
>
> **Phase 17 is the fifth item and the only one that is mostly content** — the
> Blind 75 fill-in, 53 katas taking the library from 62 exercises to 115. The
> scope was chosen by *technique gap* rather than list position: of Blind 75, 22
> were already present, and the tags said which of the rest mattered —
> `binary-search`, `stack`, `linked-lists` and `sliding-window` had one kata
> each while backtracking, tries, union-find, bit manipulation and heap-design
> had **none**, against `arrays`, `trees`, `graphs` and `dynamic-programming`
> already covered eight to nine deep. NeetCode 150's remaining ~87 are
> deliberately unscheduled for the same reason.
>
> **What the phase actually found is about its own tests.** Sixteen were wrong,
> in three kinds, and the kinds are the finding: seven wrong expected values,
> which the content suite caught immediately; **six tests that could not fail or
> did not discriminate**, which it cannot see at all, because it proves only
> that the reference passes and the stub fails; and three wrong prose claims.
> Three of the six were found by a code review *after* the ADR was written, all
> three of them timing claims that no longer held at the size chosen. Two could not fail at all: a palindrome
> counter-example that inserted a mismatching character at the *exact centre* of
> a palindrome, and an interval test whose expected value was hand-counted using
> the very arithmetic it existed to check. One was a false *claim* rather than a
> false value, and the correction is the better lesson — an impossible case that
> cannot win does not need excluding.
> [ADR 0022](adr/0022-counter-examples-are-run-against-the-bug-they-name.md)
> makes running the buggy variant part of authoring the test, and the oracles
> that back it swept 380,100 grid/word-list pairs, 140,680 trees and ~62,000
> word lists among others.
>
> **And the one number this phase cannot give you is a runtime.** The guess
> going in was that the pre-push suite would get slower, and the honest answer is
> that **this machine cannot tell**: three runs of the full gate on an idle box
> gave 5m12s, 5m27s and 12m02s, and three serial runs of
> `tests/content/test_katas.py` gave 240s, 414s and ~500s. The variance is
> larger than any effect 53 katas could have, so every precise figure in the
> first draft of this entry was a single run quoted as a fact. What *is*
> established is the shape: that file has overtaken `test_scenarios.py` (~162s)
> as the critical path, and under `--dist loadfile` a whole file lands on one
> worker, so adding katas moves the floor. The gated surface is untouched,
> because 53 katas put nothing inside it.
>
> **Phase 18 is the sixth, and the first that was asked for rather than chosen**
> — a way to put the attempt you are stuck on in front of an AI. A button in the
> workbench, or `practice context`, turns an attempt into text to paste into a
> chat: the task, every command and what it printed, the hints revealed and the
> repository as it stands, under a prompt asking the model to tutor rather than
> answer. The app still talks to nothing; it prepares a paste.
>
> **Nothing new is tracked, and that is the finding rather than a shortcut.**
> The sketch that came with the request was a recorder. `Attempt` has been one
> since Phase 1 and `InspectRepository` has read the live repository through the
> grading port since Phase 8, so the phase is a projection of state the
> application already owned, and the whole design is what the projection leaves
> out. **That boundary is a type, not an instruction**
> ([ADR 0023](adr/0023-the-tutor-context-is-what-the-solver-has-seen.md)):
> `TutorContext` has no field for a hint nobody revealed, for the author's notes
> or for a check, so the renderer cannot leak what it was never handed, and
> `tests/content/test_tutor_context.py` holds all 115 exercises to it — each
> absence paired with the presence that proves the needle could have matched.
> The better tutor, handed the answer and told not to say it, was the closest
> alternative and was turned down.
>
> **And one thing nobody went looking for.** Every exercise carries a `notes.md`
> that `practice validate` requires to be non-empty, the README calls the notes
> "the product", and **no template and no command had ever printed one.** The
> post-mortem bundle is the first surface in the application that shows an
> author's notes to the person who just finished the exercise.
>
> **Phase 19 is the same attempt, fetched instead of pasted.** `practice mcp` is
> a Model Context Protocol server on stdio: an AI client starts it, and the
> model reads the attempt you have open in the browser — and reads it again
> after your next command, which is the one thing a paste cannot do. Three
> tools, all of which read, and none that runs a command: a command the model
> ran would land in your log and be graded as yours
> ([ADR 0024](adr/0024-an-mcp-server-that-can-only-read.md)).
>
> **It is a third driving adapter and the core did not notice**, which is §2's
> claim about the CLI holding for a protocol with no HTML in it. What the phase
> found is narrower and more useful: **"read-only port" was true of
> `RepoQuery`'s contract and not of its implementation.** `read_blob` runs
> `git show <rev>:<path>`, every revision it had ever been handed came from an
> exercise author, and `git show --output=FILE` opens a file for writing. The
> first caller that is a model choosing its own arguments is the first one for
> whom that matters. The SDK is an optional extra, so the base install is
> unchanged and still carries nothing that can open a socket.
>
> **Phase 20 is the first one that came from using it.** The report was "this
> doesn't seem to have persistent memory", and the storage was fine: every
> attempt had been in SQLite since Phase 6 and nothing on screen could be asked
> about it *by exercise*. Browse looked the same on the fortieth visit as the
> first, and an exercise solved without pressing a schedule grade came back
> marked **new**. So: a done-and-when chip on every list, read off the attempt
> log rather than the card store; **tracks** — the whole library, the Blind 75,
> git scenarios, SQL drills — as a second manifest whose orders `practice
> validate` holds to the curriculum's dependencies; and a **Next** button under
> every verdict, which follows the track named in the URL
> ([ADR 0025](adr/0025-tracks-are-a-second-manifest.md)). No migration and no
> new port.
>
> **And one change since, not a phase, from using Phase 19.** The MCP server
> asked *which attempt?* whenever more than one was open, which with a single
> exercise left unfinished is every time. The app now marks the attempt in front
> of its solver — `practice start`, `practice resume`, a workbench tab coming to
> the front — and the server reads the mark instead of asking
> ([ADR 0026](adr/0026-the-current-attempt-is-a-mark-the-solver-leaves.md)).
> The fourth migration, and the first for something that is not an attempt or a
> card.
>
> **Owner:** Chris Sweet · **Plan written:** 2026-09-30 · **v1.0.0:** 2026-10-03
> · **Last phase:** 20 (tracks, and done-and-when), 2026-10-12 · **Last
> change:** the current-attempt mark, 2026-10-12

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
  constraints:
    - "2 <= len(numbers) <= 10**5"
    - "Exactly one pair of positions adds up to the target."
  examples:
    - input: |
        two_sum([2, 7, 11, 15], 9)
      output: |
        (0, 1)
      explanation: |
        2 + 7 is 9, and they sit at positions 0 and 1.
```

**`constraints:` and `examples:` arrived in Phase 21**, and the sample above is
the shape they settled into rather than the one first drafted here. An example
is two pieces of *source*: `input` is a snippet whose last line is an
expression, and `output` is an expression for its value. The content suite runs
every pair against the reference, so an example on the page is a checked claim
([ADR 0027](adr/0027-examples-are-source-run-against-the-reference.md)). Both
fields are optional in the schema and required of every shipped kata by
`tests/content/test_katas.py`. Always a block scalar: `output: [0, 1]` is a
YAML list, and the schema refuses it.

**A kata can also be a variant of another**, with a top-level block:

```yaml
id: variants/two-sum-in-a-sorted-list
variant:
  of: katas/two-sum
  twist: "The list is sorted, you get O(1) extra space, and positions count from 1."
```

A variant is a whole exercise in its own directory under `content/variants/`.
It is loaded, validated and graded like any other and **never listed**: the
curriculum does not place it, no track names it, and it is offered only under
its base ([ADR 0028](adr/0028-a-variant-is-a-whole-exercise-offered-under-its-base.md)).

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

### 5.5 SQL drill file

Phase 14's addition, and the third `kind:`. Numbered 5.5 rather than slotted in
after 5.2 because §5.3 and §5.4 have been cited by name since Phase 2 and
numbers here are never reused — the same rule the ADRs follow.

```yaml
schema_version: 1
id: sql/one-row-per-customer
kind: sql_drill
title: One row per customer, including the quiet one
difficulty: easy
tags: [joins, aggregation, nulls]
estimated_minutes: 12

prompt: |
  Read `seed.sql` first — it is in your workspace and the schema is part of
  the question.

  Return **every** customer with the number of orders they have placed, as two
  columns named `name` and `orders`, sorted by name.

hints:
  - "..."

drill:
  seed: seed.sql          # builds the starting database. Trusted code.
  stub: stub.sql          # what the solver edits. Copied into the workspace.
  reference: solution.sql # the author's answer. Never copied in.

  counter_examples:
    - file: inner-join.sql
      expect_failures: [rows-match, one-row-each, kept-the-quiet-customer]

  checks:
    - id: rows-match
      label: Every customer appears once, with the number of orders they placed
      severity: required
      assert: result_matches
      with:
        rows: [[alice, 3], [bob, 2], [carol, 1], [dana, 0]]
        ordered: true
      explanation: |
        The row that separates a right answer from a plausible one is `dana, 0`.
```

**Four things make this different from §5.2's scenario, and each is a decision.**

**`seed` is a sibling of `fixture`, not of `stub`.** It builds the starting
database the way a git fixture builds the starting repository, and like a fixture
it is trusted code. Unlike a fixture, **the solver is meant to read it** — the
schema is the question rather than the answer, and a drill with a hidden schema
is a riddle — so the provisioner copies it in. `reference` and the
counter-examples stay in the content directory: that is the answer key staying
outside the exam.

**No `allowed_commands` and no `max_commands`.** A drill has no command console,
so there is nothing to police. `AttemptPolicy.for_exercise` already encoded that
honestly for a kata — a zero budget and an empty allowlist — and a drill falls
into the same branch unchanged. §5.3's command-list guarantee therefore does not
apply here, and neither does the `|<>&;` rejection: a `.sql` file is not a
command list, and needs semicolons.

**The `assert:` vocabulary is a different one.** Ten names over `DrillQuery`
rather than twenty over `RepoQuery`, and the two sets are *deliberately
disjoint*: a drill naming `tree_equals` is rejected by the schema with the family
named, rather than reaching a dispatcher holding the wrong port. The mechanisms
§5.4 describes — negation as a uniform modifier, `severity`, the author's own
`label` and `explanation`, counter-examples naming their expected failures —
are shared unchanged, which is the evidence that those were the right shape.

**Expected rows are compared as text, and the rule is a grading policy rather
than a driver detail.** `NULL` is written as the word. A float is formatted with
`%g`, so `10.0` reads as `10` — and a drill whose answer is an average should ask
for `ROUND(AVG(x), 2)` in SQL, because controlling the precision of what you
return *is* the lesson. Row order is ignored unless the check says
`ordered: true`; column order is graded unless it says otherwise, because a
`SELECT` list is written by hand and always reproducible while row order without
an `ORDER BY` is neither.

**The craft family is advisory by convention.** `sql_matches` and
`query_plan_matches` read the solver's text and SQLite's query plan, which is the
only way to grade *how* an answer got there — the counterpart to `command_used`
on the git side, and subject to the same rule. Nothing in the domain enforces the
convention; `tests/content/test_drills.py` holds the library to it, and
`practice validate` refuses an exercise whose only *required* check reads the
text ([ADR 0019](adr/0019-sql-drills-as-a-third-exercise-kind.md)).

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
- **Enforced by test, in two halves.** `tests/web/test_offline.py` greps every
  template and static file **of ours** for `http://`, `https://` and `//cdn`;
  `tests/web/test_vendored_assets.py` checks the four third-party files against
  the SHA-256 recorded for each. The split is forced rather than chosen: a
  minified library carries its own licence URL in a banner comment, so grepping
  it would either condemn an asset that fetches nothing or be weakened until it
  caught nothing. The hash is the stronger claim anyway — the grep says *this
  file names no remote host*, the hash says *this file is the one that was
  reviewed*. A third test asserts every file under `static/` falls into one of
  the two sets, because the failure mode of a split rule is a category that
  appears between the halves and is checked by neither.
- `.gitattributes` marks the vendor directory `-text`, the one exception to the
  repo-wide LF rule. The hashes are over the downloaded bytes; normalisation on a
  Windows checkout would make the verification pass on one platform and fail on
  the other — the same trap `content/fixtures.lock` exists to catch.

### 8.3 Web security on localhost

The server executes arbitrary code by design. **Two and a half guards**, all
small — the half was added in Phase 7, after writing the other two:

1. **Loopback binding.** Startup asserts the host is `127.0.0.1`, with a test
   that fails if a future change binds `0.0.0.0`. The check lives *inside* the
   argument to `uvicorn.run`, so it cannot be deleted while rebasing.
2. **Cross-origin guard.** Binding to localhost does *not* stop a malicious
   website in your browser from POSTing to `http://127.0.0.1:8765`. Middleware
   rejects mutating requests whose `Origin` is not our own and whose
   `Sec-Fetch-Site` is not `same-origin`. Cheap, effective, and a good thing to
   be able to explain — most people assume localhost is automatically safe.

   A request that proves *nothing* — neither header present — is refused too.
   The lenient reading, "that's a non-browser client, so allow it", is what most
   localhost tools ship and it hands the whole guard to any browser that omits
   the header. The strict rule costs a browser nothing and costs `curl -X POST`
   one header; there is a CLI over the same use cases that needs no server.
3. **A loopback `Host`** — the half, and the one the pair above does not cover.
   Under **DNS rebinding**, `evil.example` resolves to 127.0.0.1, so a page
   served from it sends `Origin: http://evil.example` to a request whose own
   `Host` is `evil.example` — the two *agree* — and the browser reports
   `Sec-Fetch-Site: same-origin`, truthfully. Both named guards pass. Comparing
   `Host` against the loopback names is the only thing that sees it, and it has
   to apply to **reads as well as writes**: a rebound page that can read our HTML
   can read an attempt's transcript out of it.

### 8.4 Pages

| Route | Contents |
|---|---|
| `/` | Dashboard: due today, streak, recent attempts, weakest tags |
| `/tracks`, `/tracks/{name}` | A route through the library and your place on it (Phase 20) |
| `/browse` | Filterable exercise list (kind, difficulty, tag), each row saying whether and when it was passed |
| `/attempt/{id}` | The workbench — kata editor, or scenario console + state panel; `?track=` names the track it was started on |
| `/progress` | Mastery by tag, attempt history, time trends |

**Status is on `/browse` as something shown, not something filtered on**, which
is how the fourth dimension this table originally listed finally arrived. Phase
9 left it out on the grounds that the questions it was for were answered on
other pages; Phase 20 found the one that was not — *which of these have I
done* — and answers it with a chip per row read off the attempt log
([ADR 0025](adr/0025-tracks-are-a-second-manifest.md)).

HTMX fragments return HTML, not JSON: `POST /api/attempt/{id}/command` renders
the appended command output **and** the re-rendered repo state panel in one
response. Charts are **hand-rolled inline SVG generated in Python** — zero
dependencies, fully offline, fully server-rendered.

**Own-editor mode is two endpoints under the workbench**, added in Phase 10.
`POST /api/attempt/{id}/editor` writes what is in the browser editor to the
attempt's real file and opens the solver's editor on it;
`GET /api/attempt/{id}/watch` is a **server-sent event stream** that re-grades
the file on every save and pushes back the same verdict fragment a submission
would have rendered, plus the file's own text so the browser editor can mirror
it. It is the one endpoint in the app that is `async` and the one that is not an
HTMX swap — native `EventSource`, because htmx 2 ships SSE as a separate
extension and §8.2 would then have a fifth file to pin. A save is a **preview**:
nothing is persisted and the attempt stays open (ADR 0013).

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
   the check functions live in `domain/checks/` (§6.2), the 20 assertions fall
   inside this gate rather than outside it — which was the whole point of
   putting them there.
2. **Architecture test** — AST-walks `domain/` and `application/`, fails on any
   import from `adapters/` or `interface/`. See §3.
3. **Check-engine tests** — all 20 assert types against `FakeRepoQuery`. No git
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
│   │   ├── checks/          # registry + 20 PURE assert functions (§6.2)
│   │   │   ├── registry.py  refs.py  trees.py  worktree.py
│   │   │   └── recovery.py  process.py
│   │   ├── drills/          # registry + 10 PURE assert functions; phase 14
│   │   │   ├── registry.py  evaluation.py
│   │   │   └── rows.py  tables.py  craft.py
│   │   └── scheduling/{sm2,fsrs,suggestion}.py
│   ├── application/
│   │   ├── dto.py  registry.py  errors.py
│   │   └── use_cases/*.py
│   ├── adapters/
│   │   ├── content/{schema,loader,validation,filesystem,errors}.py
│   │   ├── persistence/memory.py        # in-memory attempts; sqlite/ in phase 6
│   │   ├── persistence/sqlite/{connection,migrations/,attempts,reviews,mappers}.py
│   │   ├── sandbox/{workspace,provisioner,command_policy,virtual_commands,env}.py
│   │   │            {execution,fixture_runner,fixture_lock}.py  # §16
│   │   │            {editor,watcher}.py   # the solver's own editor; phase 10
│   │   ├── git/{repo_query,graph}.py   # reads repos; phase 5
│   │   ├── kata/{pytest_runner,report_plugin,grader}.py
│   │   ├── sql/{engine,drill_query,grader}.py   # the drill engine; phase 14
│   │   └── clock.py  ids.py
│   ├── interface/
│   │   ├── web/{app,security,errors,vendor}.py  # vendor.py: the asset manifest
│   │   │   ├── routes/{dashboard,browse,attempt,console,editor,progress,review}.py
│   │   │   ├── templates/*.html + partials/{verdict,refusal}.html
│   │   │   └── static/app.css + vendor/   # htmx + CodeMirror 5, hash-pinned
│   │   └── cli/main.py
│   ├── composition.py
│   └── config.py
├── content/
│   ├── _lib/fixture_lib.sh          # commit_as, mkremote, publish, write_file
│   ├── fixtures.lock                # cross-platform SHA verification (phase 3)
│   └── {katas,git,sql}/…
├── tests/{unit,integration,content,web,e2e,fakes}/
└── tools/vendor_assets.py
```

---

## 11. Phases

Sequenced so every phase ends with something runnable. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/) — worth doing
because it makes the git history itself part of the portfolio.

**Each phase's commit list is a dependency order.** A commit whose module
imports something a later commit adds is a commit nobody can read on its own,
and the list below reads as a sensible *narrative* order — foundations, then the
interesting part — which is not the same thing. So check each list against the
actual imports before committing to it, and reorder rather than reaching for a
`--no-verify`-shaped workaround. `mypy` over the working tree does most of this
for free: it names the missing import, by line, without running anything.

**What this used to say, and why it does not any more.** Until Phase 11 the rule
was stronger — *every commit in a phase must be green on its own* — enforced by
a loop that checked out each commit in turn and ran lint, types and that
commit's own test directories against it. It was dropped, deliberately, and the
reasoning is worth keeping because the rule sounds unarguable:

- **It priced bisectability at more than bisectability is worth here.** The loop
  is seconds per commit only when a commit's tests are fast; with a content
  suite that walks 54 exercises it is minutes per commit, and the attribution
  loop that runs when it goes red is minutes per commit again. Phase 11 spent
  well over an hour of wall clock on verification runs, most of it re-running
  work that the pre-push suite then ran once more.
- **It cannot see a content commit at all**, because the loop derives its test
  paths from the test *directories* a commit touches and a content commit
  touches none. So the rule was already not holding for seven of Phase 11's
  thirteen commits, and claiming it did would have been the worst of both.
- **The failure it guards against is cheap to find and cheap to fix.** A commit
  that cannot stand alone is discovered the moment anyone checks it out, and the
  fix is a reorder or a squash. Nothing downstream depends on the property —
  there is no release process, no cherry-picking between branches, no bisect
  across phase boundaries.
- **`git bisect` still works.** It needs commits that *build*, which `mypy`
  gives, far more than it needs every commit to pass every test — and a bisect
  over this history would be looking for a regression in the last few commits,
  not across a phase that added fifty-one exercises.

What replaced it is one tier plus a gate, with no checkouts anywhere.

**Per commit — on the working tree, not a checkout:**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q --no-cov <the tests this change touches>
```

Seconds. No `git checkout`, so no clean-tree requirement, no editable-install
confusion, and no re-running of commits that were already fine. For a content
change the second line is `uv run pytest -q --no-cov -m content -k <slug>`,
which is about four seconds per exercise.

**Before a push — the whole suite with the coverage gate, once:**

```bash
uv run pytest --cov --cov-report=term-missing -n 4 --dist loadfile
```

This is the tier that decides, and it is exactly what CI runs on both platforms.

**Four workers, and the number is measured rather than chosen.** Every worker
spawns its own subprocesses — a bash fixture and a dozen `git` invocations per
scenario, a `pytest` per kata — so the useful worker count tracks subprocess
load, not cores. On a twelve-core machine, with the coverage gate:

| workers | wall clock | repeatable? |
|---|---|---|
| serial | 10m10s | yes |
| `-n 4` | **7m20s** | yes |
| `-n auto` (12) | 3m42s, then 7m36s, then 8m41s | **no** |

`-n auto` is the trap. Its best run is the fastest number here and its times
swing by more than a factor of two, because twelve workers each starting
processes oversubscribe a twelve-core machine — and one of those runs *failed*,
by taking a kata's grading past the ten-second wall-clock limit the suite holds
it to on purpose (§16). Four workers are faster on average and repeatable, which
is the property that matters in the tier that decides.

`--dist loadfile` rather than the default `load`, because every test in a file
then lands on one worker, which is what keeps the content suite's module-scoped
workspaces and memoised verdicts shared instead of rebuilt per worker.

Deliberately **not** in `addopts`: four workers to run one file is slower than
one, and the fast tier runs one file. `-n0` turns it off. CI uses `-n auto`
rather than `-n 4` for the same reason this machine does not — a GitHub runner
has two cores, so `auto` is two workers there and matches the principle instead
of fighting it.

Three things worth knowing about the fast tier, all found by using it.

**Nothing else may be running.** The one that wasted the most time: a suite
competing with another for temp directories, SQLite files and subprocesses fails
in ways that look like real defects and are not — and `--cov` makes it worse,
because two runs share one `.coverage` in the project root and will report a
module at 60% that is fully covered. Run one thing at a time, and suspect this
before debugging a failure you cannot reproduce.

**After changing any user-facing string, `grep -rn` for it.** The defect the
fast tier reliably misses is a test asserting on a *string* — an error message, a
refusal, a caveat — in a directory the change did not touch. Phase 5 changed an
error message; Phase 6 turned a `gc` refusal into a collection and left a test
matching the literal `"phase 6"`. `mypy` cannot see either, because neither is a
type. One `grep -rn` is cheaper than the full suite and is the only check that
covers this case directly.

**A content change is only covered by `-m content` and `tests/e2e`.** Phase 11's
one escaped defect was neither a schema error nor a wrong check: the dashboard
offers the top six rows of the queue, and a library that grew from 3 exercises to
54 moved the exercise an e2e test asks for off the first screen. Nothing but the
e2e suite reads the real library through the real web app, so nothing else could
have noticed. The durable fix was a content test asserting the property directly
(`test_the_first_screen_of_the_curriculum_offers_both_kinds`), which is the
general move: when the full suite catches something, push the claim down into the
fastest suite that can hold it.

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

### Phase 7 — Web shell and kata workbench · 4 sessions — **complete**

- FastAPI app, base templates, loopback assertion, cross-origin middleware
- Vendored htmx + CodeMirror with a hash-pinned fetch script
- `/browse` and the kata workbench
- HTMX submit flow with a verdict panel

**Commits**
1. `chore(web): vendor htmx and codemirror for offline use`
2. `feat(web): add FastAPI app, base templates and loopback guard`
3. `feat(web): add browse and kata workbench pages`
4. `feat(web): add htmx submit flow with verdict panel`
5. `docs: add ADRs 0007 and 0010 and mark phase 7 complete`

Vendoring comes first because the base template references the vendored files by
path. The other way round, commit 1 ships a layout whose `<script>` 404s —
which the offline-asset test would not catch, because it greps for `http://`
and a broken local path is not a remote one.

**Exit:** a kata solved entirely in the browser with the network disconnected.
Offline-asset test green. **Both met** — the first by
`tests/e2e/test_solve_a_kata_in_the_browser.py`, which browses, starts, submits a
near-miss, reads the verdict, fixes it and passes, over real adapters and a real
pytest run; the second by `tests/web/test_offline.py`, which greps every template
and stylesheet of ours for a remote reference, asserts the walk found something,
and asserts that every file under `static/` is covered by either that grep or the
SHA-256 pinning in `tests/web/test_vendored_assets.py`.

The commit list needed one addition, recorded in §16 rather than edited away:
**`practice serve`**, without which the exit criterion is untypeable. The same
omission Phase 6 found with `practice start`, in the same shape.

---

### Phase 8 — Git scenario workbench · 4 sessions — **complete**

- Command console with HTMX-appended history
- Repo state panel: HEAD, refs, status, stash
- Commit graph — text lanes first, then the SVG renderer
- Progressive hint reveal and verdict breakdown with explanations

**Commits**
1. `feat(web): add scenario command console with htmx history`
2. `feat(web): render repo state panel with refs and status`
3. `feat(web): add commit graph renderer`
4. `feat(web): add hint reveal and verdict breakdown`
5. `docs: add ADR 0012 and mark phase 8 complete`

**Exit:** a git scenario driven start to finish in the browser, with the graph
visibly changing after each command. **Met** by
`tests/e2e/test_solve_a_git_scenario_in_the_browser.py`, which browses, starts,
inspects, hits the no-shell refusal, reveals a hint, reverts, pushes and submits
over real adapters — asserting on the way that the panel came back out of band with
each command and that the graph had grown a commit by the end. Unlike Phases 6 and
7 the commit list needed no additions; what this phase needed was a port moved
(§16).

The two defects this phase found are both in the graph, and both are the kind that
pass a casual look: an edge built from a lane *reservation* rather than from the
finished row points at a column the parent is not drawn in, and a lane left
reserved after the commit it was waiting for is drawn elsewhere pushes every later
branch a column right. Neither is visible on a linear history, which is what a
fixture mostly has.

---

### Phase 9 — Spaced repetition and progress · 3 sessions — **complete**

Turns a quiz app into a training system.

- SM-2 (four-grade Anki variant) as a pure function, with property tests —
  including the `max(previous + 1, ...)` interval clamp the monotonicity
  property requires (§9, item 7)
- Review queue plus an auto-suggested grade from verdict, elapsed time and hints
  used
- Dashboard: due queue, streak, weakest tags
- Progress page with inline-SVG charts

**Commits** — seven, where the plan sketched four (§16)
1. `feat(domain): add SM-2 scheduler with property tests`
2. `feat(app): add review queue and grade suggestion`
3. `feat(web): schedule a review from the verdict panel`
4. `feat(app): summarise progress from the attempt history`
5. `feat(web): add dashboard with due queue and streak`
6. `feat(web): add progress page with tag mastery charts`
7. `test(e2e): schedule a review and see the dashboard change`
8. `docs: add ADR 0008 and mark phase 9 complete`

**Exit:** "what should I practice today?" is answered by the tool, not by you.
**Met** by `tests/e2e/test_schedule_a_review.py`, which over real adapters asks
the dashboard, solves the kata it offers, takes the grade the tool proposes, and
asks again — and gets a different answer. The four properties §9.7 states are
met by `tests/unit/domain/scheduling/test_sm2.py`, each named after its bullet.

**MVP ends here.** Phases 0–9 are a complete, genuinely useful product.

---

### Phase 10 — Own-editor mode · 2 sessions — **complete**

- Scaffold the kata into a real file on disk; reveal it in the editor
- `watchfiles` watcher plus an SSE endpoint that re-grades on save

**Commits** — three, where the plan sketched two (§16)
1. `feat(workspace): add file mode scaffolding and reveal in editor`
2. `feat(web): stream grade-on-save results over SSE`
3. `docs: add ADR 0013 and mark phase 10 complete`

**Exit:** save in VS Code, see the verdict update in the browser. **Met** by
`tests/e2e/test_solve_a_kata_in_my_own_editor.py`, which over real adapters
reveals the file, has a real editor process write a solution into it, watches a
real `watchfiles` watcher notice the save, grades it with a real pytest run, and
reads the verdict fragment off the event stream — then asserts the attempt is
still open and its log holds no solution, which is ADR 0013 as a test. The
scaffolding half is met by `tests/unit/application/test_reveal_solution_file.py`
and `tests/integration/sandbox/test_editor.py`, and the "nothing is scaffolded,
because the stub already is the working copy" finding is in §16.

---

### Phase 11 — Content build-out · 8+ sessions — **complete**

The phase that determines whether you actually use this thing. Planned as pure
authoring with no code changes — the payoff of §5 — and it was *nearly* that:
51 exercises, 3 small code commits, and the three code commits are the
interesting part of the record (§16).

Git tracks (24 scenarios): history rewriting · recovery & bisect ·
collaboration & conflicts.
Kata tracks (30 katas): arrays/strings/hashing · trees & graphs · DP & greedy.

**Commits** — thirteen, where the plan sketched seven
1. `content(git): add history rewriting track`
2. `content(git): add recovery and bisect track`
3. `feat(content): let a reference solution declare its failing commands`
4. `fix(checks): share one definition of what a fixture alias is`
5. `content(git): add collaboration and conflict track`
6. `content(katas): add arrays, strings and hashing track`
7. `content(katas): add trees and graphs track`
8. `content(katas): add dynamic programming and greedy track`
9. `refactor(checks): delete the two assertions Phase 11 did not need`
10. `content: add curriculum manifest with track ordering`
11. `fix(content): put both kinds on the curriculum's first screen`
12. `docs(content): correct three claims found reviewing the notes`
13. `docs: add ADRs 0009 and 0014 and mark phase 11 complete`

Commits 11 and 12 are the pre-push run and a read-through finding things the
per-exercise tier could not: one about what the *library* offers rather than
what any exercise does, and three claims in notes that were wrong rather than
unproven (§16).

**Exit:** ≥ 50 exercises, all green under the content integrity suite. **Met** at
**54** — 24 git scenarios and 30 katas — by `uv run pytest -m content`, which is
936 cases over the real `content/` directory. Per exercise it is the four files
of §9 doing the work, and each criterion has a named owner:

- *solvable* — `tests/content/test_scenarios.py` replays every `solution.cmds`
  through the real use cases and requires every required check to pass;
  `tests/content/test_katas.py` grades every `solution.py` with a real pytest
  run.
- *discriminating* — the same scenario suite requires each counter-example to
  fail **exactly** its declared checks, in both directions. 52 counter-examples
  across 24 scenarios, and it corrected five of my own predicted failure sets.
- *not vacuous* — per kata, `test_its_stub_fails` and
  `test_its_hidden_suite_holds_more_than_one_test`; per scenario,
  `test_at_least_one_required_check_is_proven_to_discriminate`.
- *reproducible* — `practice fixtures --check` holds all 24 fixtures to
  `content/fixtures.lock`, on Linux and Windows.
- *well-formed* — `practice validate` audits all 54 without executing anything,
  and now also requires `content/curriculum.yaml` to place every one of them.

The three unplanned code commits are each a case of content finding a gap in the
engine rather than a change of direction: `reference_failing_commands` exists
because a conflict scenario's answer *starts* with a command that exits 1;
`alias_name` because `@{u}` is a git revision and the content suite thought it
was a fixture alias; and the deletion because the two assertions Phase 5 flagged
as unproven stayed unused across all 24 scenarios, which is what §13 said to do
about them.

---

### Phase 12 — Polish and portfolio artifacts · 3 sessions — **complete**

- `practice` launcher: first-run setup, migrations, browser open
- README with the architecture diagram and a demo GIF
- Remaining ADRs plus an honest "what I'd do differently" postmortem
- Tag `v1.0.0`

**Commits** — four, exactly as sketched, which had not happened before
1. `feat: add launcher with first-run setup`
2. `docs: add README with architecture diagram and demo`
3. `docs: add remaining ADRs and a project postmortem`
4. `chore(release): tag v1.0.0`

**Exit:** a stranger can clone, run one command, and be practicing in under two
minutes. **Met**, and the criterion is a test rather than a claim:
`tests/integration/test_cli_up.py::test_a_clean_machine_is_set_up_in_one_command`
starts with no database and no workspace root, runs `practice up` once, and
requires a migrated database file, a created workspace directory, a browser
opened on the bound URL and a server started. Each clause of the criterion has
a named owner:

- *one command* — `practice up`, which runs the four preflight steps, creates
  what it can and hands the same object graph to the same `uvicorn.run`
  ([ADR 0017](adr/0017-a-front-door-separate-from-the-server.md)).
- *under two minutes* — `uv sync` against a lock file resolved at Phase 0, then
  one command. Nothing is downloaded at run time, which is the offline claim
  (§8.2) doing double duty.
- *a stranger* — the refusal tests, which are where this command earns its
  keep: no git, an empty library, a library with one unloadable exercise, a
  database written by a newer `practice`, and two blockers reported in one pass
  rather than one per run.

**Three deviations from the plan**, all recorded in §16: the demo is a generated
animated SVG rather than a recorded GIF
([ADR 0016](adr/0016-a-generated-demo-not-a-recorded-one.md)); the launcher is a
*second* command rather than a change to `serve`, because `serve` has a contract
the test suite depends on; and one of the three ADRs is Phase 11's, promoted out
of this plan and into the record it belonged in
([ADR 0015](adr/0015-verify-on-the-working-tree-not-every-commit.md)).

---

### Phase 13 — Stretch (post-v1, pick by appetite) · **FSRS taken, 1 session**

Each one is intended to be an **adapter or content addition, not a rewrite** —
which is the real test of whether the architecture earned its keep.

| Idea | Touches | Status |
|---|---|---|
| FSRS scheduler | a new `Scheduler` implementation only | **done** ([ADR 0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)) |
| Docker sandbox adapter | a new `SandboxProvisioner` implementation only | open |
| Shell/CLI drills (grep, awk, jq, logs) | new exercise kind + content | open |
| Concept recall with rubric self-grading | new exercise kind + content | open |
| Embedded terminal (xterm.js + pty) | a new interaction adapter | open |
| SQL drills against seeded SQLite | new exercise kind | open |
| Exportable content packs | a content repository adapter | open |
| Interview mode (timed, no hints, no test peeking) | application-layer policy | open |

**FSRS was taken first because it was the only one with a prediction attached.**
[ADR 0008](adr/0008-sm2-first-with-fsrs-behind-a-port.md) deferred FSRS in Phase
9 and wrote down, in advance, what the swap would cost: *"a second class
satisfying the same protocol and one line in `composition.py`"*, plus a migration
that *"would add columns rather than reuse them"*. Every other row in the table
would have produced a feature; this one produced a **graded prediction**, which
is worth more at this point in the project than another exercise kind. It also
cleared the one port that had been satisfying §13's two-implementation rule on an
IOU.

**Commits** — five, in dependency order
1. `feat(domain): add FSRS memory state to the review card`
2. `feat(domain): schedule with FSRS behind the Scheduler port`
3. `test(domain): hold both schedulers to one conformance suite`
4. `feat: choose the scheduler at the composition root`
5. `docs: close phase 13 with ADR 0018`

**Exit:** a second scheduler is selectable in the shipped product, and it
arrives as an addition rather than as a change to anything that was already
working. **Met**, and each clause has a named owner:

- *a second implementation* —
  `tests/unit/test_ports.py::test_the_fsrs_scheduler_satisfies_the_scheduler_port_too`
  for the shape, and
  `tests/unit/domain/scheduling/test_fsrs.py` (37 tests) for the arithmetic.
- *selectable in the shipped product* —
  `tests/integration/test_cli_up.py::test_the_scheduler_can_be_chosen_for_real`
  sets `PRACTICE_SCHEDULER=fsrs`, runs `practice up`, and requires it to serve
  with FSRS named in the first-run report. A scheduler nobody can select is
  written, not shipped, which is the one thing ADR 0008's prediction missed.
- *an addition rather than a change* — `tests/unit/test_architecture.py` is
  unchanged and still passes, and `git diff --stat v1.0.0..HEAD -- src/` is the
  evidence: twelve files, of which **none is a use case, a grader or a route**,
  and nothing under `application/`, `domain/checks/`, `adapters/sandbox/`,
  `adapters/git/`, `adapters/kata/` or `adapters/content/` was touched at all.
  What did change: `domain/scheduling/fsrs.py` (new), two nullable fields on
  `ReviewCard`, migration 0002, the two column names in the SQLite mapper and
  the review repository's column tuple, a registry in `composition.py`, a
  question in `config.py`, a step in the launcher, and a branch in one template.
  The persistence pair is the honest asterisk on "one line at the composition
  root" — a new column has to be named where rows are built, and ADR 0008
  predicted exactly that cost.
- *the port is proved rather than claimed* —
  `tests/unit/domain/scheduling/test_scheduler_conformance.py`, parametrized over
  both, plus `test_every_real_scheduler_is_covered_here` so a third
  implementation cannot be added without being held to it.

**Three findings, all in §16.** Three of §9.7's four properties belong to the
port and one belongs to SM-2; §9.7's interval clamp is a property of whole-day
intervals rather than of SM-2's arithmetic; and the schedule panel had been
printing a number that is meaningless under FSRS, which no fragment assertion
could have caught.

---

### Phase 14 — SQL drills: the third exercise kind · **2 sessions**

Taken from Phase 13's menu, and taken second for the same reason FSRS was taken
first: **it was the item with a prediction attached.** `domain/exercise.py` has
claimed since Phase 1 that "adding a third kind means adding a spec and a
registry entry instead of re-cutting a class hierarchy", and
`application/registry.py` kept `_PENDING` deliberately empty against the day one
arrived. Two kinds is the number at which a discriminated union and an
inheritance hierarchy are indistinguishable, so the claim had no evidence behind
it.

It is also the row on the menu that applies the **core bet to a second domain**.
*Grade the end state, not the answer text* is nearly free for a `SELECT` — the
rows are the end state — and only becomes a claim worth testing for an `UPDATE`
or a `DELETE`, which return nothing at all.

| Idea | Touches | Status |
|---|---|---|
| FSRS scheduler | a new `Scheduler` implementation only | **done** ([ADR 0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)) |
| SQL drills against seeded SQLite | new exercise kind | **done** ([ADR 0019](adr/0019-sql-drills-as-a-third-exercise-kind.md)) |
| Docker sandbox adapter | a new `SandboxProvisioner` implementation only | open |
| Shell/CLI drills (grep, awk, jq, logs) | new exercise kind + content | open |
| Concept recall with rubric self-grading | new exercise kind + content | open |
| Embedded terminal (xterm.js + pty) | a new interaction adapter | open |
| Exportable content packs | a content repository adapter | open |
| Interview mode (timed, no hints, no test peeking) | application-layer policy | open |

**Commits** — five, in dependency order
1. `feat(domain): a read-only port over a drill result, and ten assertions`
2. `feat(adapters): run a drill answer in memory, under SQLite's own policy`
3. `feat: the SQL drill kind, from spec to registered grader`
4. `content(sql): eight drills, graded end to end`
5. `docs: close phase 14 with ADR 0019`

The list is five rather than the seven the phase was sketched with, and **the
merge is the first finding**: the kind, its schema, its grader and its interface
had to land in one commit, because `test_every_exercise_kind_has_a_grader`
forbids a kind existing in the enum without a grader. The incremental path
`_PENDING` was built for is one the suite rules out. §16 has the rest.

**Exit:** a third exercise kind is solvable in the shipped product, and it
arrives as an addition rather than as a change to anything that was already
working. **Met on the first clause, and the second needs an asterisk** — which
is the phase's value. Each clause has a named owner:

- *a third kind, graded* — `tests/content/test_drills.py` (113 tests) replays
  every reference through the real grader, requires each to pass with no
  advisories, requires each stub to fail, and holds every counter-example to
  failing **exactly** the checks it declares. That is the git scenarios'
  standard (§5.4), which katas still do not meet.
- *solvable in the shipped product* —
  `tests/e2e/test_solve_a_sql_drill.py::test_a_drill_goes_from_failing_to_passing`
  drives `practice solve` from a FAIL on the stub to a PASS, and
  `tests/web/test_workbench.py` renders the drill workbench with the right
  CodeMirror mode. ADR 0018's lesson applied to a kind: one nobody can open is
  written, not shipped.
- *the port is proved rather than claimed* —
  `tests/integration/sql/test_conformance.py` holds `SqliteDrillQuery` and
  `FakeDrillQuery` to the same answers on every state a real database can
  reach, which is what makes the 86 unit tests under `tests/unit/domain/drills/`
  evidence about the engine rather than about the fake.
- *an addition rather than a change* — **the asterisk.**
  `git diff --stat v1.0.0..HEAD` is the evidence, and it says the prediction was
  half right. Nothing under `domain/checks/`, `adapters/git/`, `adapters/kata/`
  or `application/use_cases/` changed in substance; no port was widened; no
  grader but the new one was touched. What *did* change is five call sites that
  had learnt to read `isinstance(spec, KataSpec)` as *has a file to edit*, one
  architecture rule, and one template. `editable_source` is where that cost was
  concentrated, deliberately, so a fourth kind pays none of it again.

**Six findings, all in §16.** The enum-to-grader invariant makes `_PENDING`
unreachable, so it is deleted; the old `if scenario ... else kata` was asserting
that not-a-scenario means a kata; the first-run library line counted by
subtraction; §15 Q3's vendored-asset prediction was *nearly* right and the gap
fails silently; `ParamValue` had no `float`; and three content bugs that only
running the content could find, including a `LIMIT` that was vacuous on the data
it was written against.

---

### Phase 15 — Interview mode: a policy over everything already shipped · **1 session**

The third item from Phase 13's menu, and the first taken for a different reason
than the two before it. FSRS and SQL drills were both chosen because a
*prediction* was attached; this one was chosen because its prediction is in the
menu itself. The **Touches** column says `application-layer policy`, Phase 14's
log called it "the cheapest item and the most self-contained", and neither claim
had been tested. It is also the only row that changes nothing about what the
library contains and everything about how it can be sat — 62 exercises, a second
way to do all of them.

| Idea | Touches | Status |
|---|---|---|
| FSRS scheduler | a new `Scheduler` implementation only | **done** ([ADR 0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)) |
| SQL drills against seeded SQLite | new exercise kind | **done** ([ADR 0019](adr/0019-sql-drills-as-a-third-exercise-kind.md)) |
| Interview mode (timed, no hints, no test peeking) | application-layer policy | **done, with one clause scoped down** ([ADR 0020](adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md)) |
| Docker sandbox adapter | a new `SandboxProvisioner` implementation only | open |
| Shell/CLI drills (grep, awk, jq, logs) | new exercise kind + content | open |
| Concept recall with rubric self-grading | new exercise kind + content | open |
| Embedded terminal (xterm.js + pty) | a new interaction adapter | open |
| Exportable content packs | a content repository adapter | open |

**Commits** — six, in dependency order
1. `feat(domain): interview mode as a mode on the attempt policy`
2. `feat(domain): give the grade suggestion the denominator it never had`
3. `feat: start an attempt in interview mode, and stop handing over its workspace`
4. `feat(interface): offer the mode where it can be chosen, and withdraw what it withdraws`
5. `test(e2e): sit an interview, and prove the mode is not re-chosen`
6. `docs: close phase 15 with ADR 0020`

Six rather than the five the phase was sketched with, and the extra one is the
e2e test standing alone because it is the only thing in the phase that asserts
the claim the whole design rests on — see the exit criteria below.

**Exit:** interview conditions are selectable on every shipped exercise, and the
mode is decided once rather than re-read. **Met on both clauses, and the menu's
own description is what needed scoping** — which is the phase's value. Each
clause has a named owner:

- *selectable, in both surfaces* —
  `tests/integration/test_cli_lifecycle.py` for `practice start --interview`
  (nine tests, including that `solve` has no such flag and why), and
  `tests/web/test_workbench.py::test_starting_with_the_box_ticked_opens_an_interview`
  for the Start form. ADR 0018's lesson applied again: a mode nobody can select
  is written, not shipped.
- *decided once rather than re-read* —
  `tests/e2e/test_sit_an_interview.py` is the only test that can hold this, and
  it is why that commit is its own. Four invocations, one `--interview`:
  `resume` and `submit` are never told about the mode and must still apply it. A
  mode read from a flag each time would pass every other test in the phase.
  `tests/integration/persistence/test_attempts.py` holds the other half — the
  policy comes back off the row under the rules it was stored with.
- *an addition rather than a change* — closer than Phase 14 managed, and for an
  uncomfortable reason. Nothing under `adapters/sandbox/`, `adapters/kata/`,
  `adapters/git/`, `adapters/sql/`, `domain/checks/` or `domain/drills/` changed
  at all; no port was widened; no grader, fixture or exercise was touched. But
  the sandbox is untouched because the clause that would have reached it was
  **dropped**, not because it was free — see the asterisk.
- *the invariants are enforced twice, as the project's pattern requires* —
  `AttemptPolicy.__post_init__` refuses to *reach* a half-configured mode and
  migration 0003's CHECKs refuse to *store* one, in both directions.
  `tests/integration/persistence/test_attempts.py` exercises the schema's half
  in raw SQL, because there is no way to get there through the domain.

**The asterisk, and it is the whole reason this phase was worth taking.** "No
test peeking" is not implementable, by this project or any other. A kata's
`tests.py` is copied into the workspace because `pytest` must run it from there,
the workspace is a directory on the solver's own machine, and §8.1 settled in
Phase 3 that the solver owns the machine — the sentence
`adapters/sandbox/command_policy.py` opens with. So what shipped is the weaker
and honest thing: every affordance the tool provides for peeking is withdrawn,
and the tool says that is what it did.
`AttemptPolicy.reveals_workspace` is named for what it does rather than for what
would have sounded better. ADR 0020 spends its longest alternative on the
stronger version — move the tests outside `repo/` — and rejects it for widening
`SandboxProvisioner.provision` to buy a boundary that still would not be one.

**Five findings, all in §16.** Withholding hints cost no code path and one
sentence, which is §4.3 paying off exactly as claimed; the grade rule needed no
new deadline comparison because it was already making it; the review panel had
been printing "no hints" as though it were restraint, which is the Phase 13
ease-factor defect repeating in a second place; `practice solve` cannot be put
into interview mode at all; and flooring the clock greeted a fresh fifteen-minute
interview with "14 minutes left of 15", which only running it could find.

---

### Phase 16 — Content packs: the library as something you can send · **1 session**

The fourth item from Phase 13's menu, and the first that the project nominated
for itself. Phase 15's revision log closed by naming it: *"exportable content
packs are now the cheapest item on the menu and the only one that would give a
port its second real implementation."* That is two predictions in one sentence —
one about cost, one about §13 — and the **Touches** column adds a third by
saying the whole thing is *a content repository adapter*.

| Idea | Touches | Status |
|---|---|---|
| FSRS scheduler | a new `Scheduler` implementation only | **done** ([ADR 0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)) |
| SQL drills against seeded SQLite | new exercise kind | **done** ([ADR 0019](adr/0019-sql-drills-as-a-third-exercise-kind.md)) |
| Interview mode (timed, no hints, no test peeking) | application-layer policy | **done, with one clause scoped down** ([ADR 0020](adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md)) |
| Exportable content packs | a content repository adapter | **done, and the column was wrong in a useful direction** ([ADR 0021](adr/0021-content-packs-install-rather-than-mount.md)) |
| Docker sandbox adapter | a new `SandboxProvisioner` implementation only | open |
| Shell/CLI drills (grep, awk, jq, logs) | new exercise kind + content | open |
| Concept recall with rubric self-grading | new exercise kind + content | open |
| Embedded terminal (xterm.js + pty) | a new interaction adapter | open |

**It is the last port that was taking §13's two-implementation rule on credit.**
`ContentRepository` had `FilesystemContentRepository` and a fake, which is the
arrangement §13 accepts and the weakest version of it: a protocol whose only
real implementation is the one it was extracted from has not been shown to
abstract anything. It also carried the thinnest docstring in `ports.py` — one
line — which is usually a sign nobody has had to think about what a thing
promises.

**Commits** — six, in dependency order
1. `refactor(content): a parsing core that has never heard of a disk`
2. `feat(content): a library as one deterministic file, with its own digests`
3. `feat(content): read the library out of a pack`
4. `feat(interface): export a pack, check one, and install one`
5. `test(e2e): install a pack, and solve out of what it installed`
6. `docs: close phase 16 with ADR 0021`

Six rather than five, and the extra one is the e2e test standing alone for
Phase 15's reason: it is the only thing in the phase that can hold the claim the
whole design rests on, and every other test would pass without it.

**Exit:** the library can be exported as one file, verified, and installed
somewhere else as a library that works — and it arrives as an addition rather
than as a change to anything that was already working. **Met on both clauses,
and the menu's `Touches` column is what needed correcting** — which is the
phase's value. Each clause has a named owner:

- *the port has a second real implementation* —
  `tests/integration/content/test_pack_repository.py` (19 tests). The one worth
  reading is `test_both_build_identical_aggregates`: `Exercise` is a frozen
  dataclass the whole way down, so one assertion compares every field of every
  check of every spec across both implementations. `test_nothing_is_extracted`
  is the other half, because a repository that unpacked to a temporary
  directory and delegated would be §13's forbidden abstraction-forwarding-one-
  call and would prove only that `extractall` works.
- *exported, verified and installed in the shipped product* —
  `tests/integration/test_cli_pack.py` (19 tests) drives all three modes of
  `practice pack` and their refusals. ADR 0018's lesson for the third time: a
  format nobody can write and a pack nobody can install are written, not
  shipped.
- *an installed pack is a library that works* — two suites, because the claim
  has two halves. `tests/content/test_pack.py` (11 tests) round-trips the real
  62-exercise library and holds the installed root to `validate_library`, whole
  and as a SQL-only subset; `tests/e2e/test_install_a_content_pack.py` grades a
  kata and a git scenario out of an installed root with nothing pointing at
  `content/`. Only the second can say anything about solvability, for the
  reason in the asterisk.
- *determinism survives the format* — `test_exporting_twice_gives_identical_bytes`
  at both sizes, and `test_an_installed_library_is_byte_identical_to_the_source`
  over all 355 exercise files. The second is the Phase 3 line-ending claim
  stated directly: a fixture that gained CRLF in transit builds a *different and
  valid-looking* history, so the e2e scenario test grades the reference against
  the pinned checks as the backstop.
- *an addition rather than a change* — `git diff --stat v1.0.0..HEAD -- src/`
  is the evidence. Nothing under `adapters/sandbox/`, `adapters/kata/`,
  `adapters/git/`, `adapters/sql/`, `domain/checks/`, `domain/drills/` or
  `application/` changed at all; no port was widened; no grader, fixture or
  exercise was touched. Two new modules in `adapters/content/`, a text-taking
  half added to two existing ones, one widened error type, one command, and one
  docstring on the port.

**The asterisk, and it is the whole reason this phase was worth taking.**
*A content repository adapter* is one adapter, and it is not enough.
`SandboxProvisioner` is constructed with a `content_root: Path` and resolves
`content_root / exercise_id` itself, so a fixture, a stub, a `tests.py` and a
`seed.sql` reach a workspace by being copied from a directory and **never
through the port**. The library therefore has two readers: the port is the
*catalogue* — everything that reads *about* an exercise, which is browsing,
filtering, scheduling, validating and counting — and the provisioner is the
*content*. A pack satisfies the first for free and the second not at all, so a
pack-backed library can be browsed and not solved.

What ships is the install step, and ADR 0021 spends its longest alternative on
the widened port that would have avoided it — rejected because **the files have
to be written to a directory either way.** `pytest` runs a kata's tests from the
workspace, `bash` executes a fixture from a file, SQLite reads `seed.sql`; a
port carrying bytes moves the extraction inside `provision` and makes it happen
per attempt instead of once. Same work, done more often, in the one function
that is hardest to test. The finding is now written on `ContentRepository`
itself rather than left in the record, so the next person does not rediscover
it.

**Five findings, all in §16.** A pack's two indexes have to be *derived* rather
than copied or a subset installs to a library that fails both CI commands; the
determinism claim extends to the archive and nearly did not; `__pycache__` in
the content tree would have made packs non-deterministic for a reason invisible
in a diff; the export reads its own pack back because that is the only cheap way
to check the derivation; and `practice solve`'s `--content-root` turned out to
be the whole of what an installed library needs, which is ADR 0017's
`--content-root` paying off in a phase that did not plan to use it.


### Phase 17 — The Blind 75 fill-in: 53 katas, and the tests that were wrong about their own point · **1 session**

The fifth stretch item and the first that is mostly content rather than code.
Phase 13's menu does not list it, because it is not a feature — it is the thing
§11 said the library would need eventually: the kata half was 30 exercises
against a git half that was already the deeper of the two.

**The scope question is the interesting part of the planning.** "Add the Blind
150" names no real list, and the useful answer came from the *tags* rather than
from either candidate list. `arrays`, `dynamic-programming`, `trees` and
`graphs` were already eight to nine deep; `binary-search`, `stack`,
`linked-lists` and `sliding-window` had one kata each; backtracking, tries,
union-find, bit manipulation and heap-design had none. So the rule was **fill by
technique gap, not by list position**, which selects Blind 75's 53 missing
exercises and explicitly declines NeetCode 150's remaining ~87 as additional
reps inside families already covered.

**Exit criteria.**

| Criterion | Met by |
|---|---|
| Every technique Blind 75 teaches is in the library | `content/curriculum.yaml`, 21 tracks, and the five new ones for the families that were at zero |
| Every new kata's reference passes and its stub fails | `tests/content/test_katas.py`, parametrized over `content/` |
| Every new kata is named exactly once in the curriculum | `uv run practice validate` — 115 exercises, all valid |
| No exercise added code to the gated surface | coverage at 2,430 statements, unchanged by this phase's commits |
| The library still packs and installs | `tests/content/test_pack.py`; `practice pack` reports 115 exercises, 622 files, 726 KB |
| The first screen still offers every kind | `test_the_first_screen_of_the_curriculum_offers_every_kind` |

**One finding, and it is about the tests rather than the content.** Sixteen
adversarial tests were wrong about the bug they named. Seven were wrong expected
values and the content suite caught those at once; six could not fail or did not
discriminate, which it cannot see at all, since it proves only that the
reference passes and the stub fails. That earned
[ADR 0022](adr/0022-counter-examples-are-run-against-the-bug-they-name.md),
which makes executing the buggy variant part of authoring the test, and it is
the first ADR here about **how content is authored** rather than how code is
arranged.

**One thing measured, and one thing that could not be.** The curriculum was
reordered, not appended to, because appending had produced 43 consecutive katas
before the next git exercise — and strict alternation is now impossible at 14
kata tracks against 7 git and sql ones, so the manifest header records the
achievable bound of two. The runtime claim is the one that failed: three gate
runs on an idle machine spread from 5m12s to 12m02s, which is wider than
anything the content could have caused, so "the suite did not get slower" is not
a statement this phase is entitled to make. The critical path did move —
`tests/content/test_katas.py` has overtaken `test_scenarios.py` — and that part
is a ranking rather than a duration, which is why it survives the noise.

### Phase 18 — The tutor context: an attempt, projected for somebody else to read · **1 session**

The sixth stretch item, and like Phase 17 it is not on Phase 13's menu. The
request was *an easy way to ask an AI about the scenario I am in*, with a sketch
attached — a JSON file that tracks what you do as you go, with a prompt in it
that makes a chat model a tutor.

**The planning question was what there was left to build, and the answer was
less than the sketch assumed.** `Attempt.events` has held every command with its
output and every hint with its index since Phase 1, because the process
assertions and the grade suggestion read it. `InspectRepository` has read the
live repository through the grading port since Phase 8. So nothing needed
tracking. The phase is a *projection* — one use case and a renderer — and the
whole of the design is what the projection leaves out.

**Commits** — seven, in dependency order
1. `feat(domain): let the attempt policy say whether a tutor is on offer`
2. `feat(application): project an attempt into what its solver has already seen`
3. `feat(application): render the tutor context as markdown and json`
4. `feat(cli): print the tutor context for an attempt`
5. `feat(web): copy the tutor context from the workbench`
6. `test: hold every exercise to the spoiler boundary, and ask mid-scenario end to end`
7. `docs: close phase 18 with ADR 0023`

**Exit criteria.**

| Criterion | Met by |
|---|---|
| A bundle exists for every exercise kind, from both surfaces | `tests/web/test_tutor.py` for the workbench panel, `tests/integration/test_cli_context.py` for `practice context` |
| An open attempt's bundle holds no hint nobody revealed, no notes and no check | `tests/content/test_tutor_context.py`, parametrized over all 115 exercises |
| Each of those absences could have been a presence | the same file: a hint is found verbatim once revealed, and the notes and every check label once a verdict exists (ADR 0022) |
| A kata's hidden suite is not reachable | `test_a_katas_hidden_suite_is_not_reachable_at_all`, over all 83 katas |
| The bundle is the attempt at the moment it is asked for | `tests/e2e/test_ask_for_help_mid_scenario.py` — four bundles across one real attempt |
| The repository a tutor is told about is the one the panel shows | `test_an_open_scenario_carries_the_repository_the_panel_shows`, by equality with `InspectRepository` |
| An open interview is refused on every surface, and a finished one is not | `tests/unit/application/test_export_tutor_context.py`, plus one refusal each in the web and CLI suites |
| Exporting writes nothing | `test_exporting_records_nothing_on_the_attempt`, `test_preparing_records_nothing` |
| An addition rather than a change | `tests/unit/test_architecture.py` is unchanged; no port, no adapter, no migration and no dependency |

**The one change to code that already existed** is `_view` in
`inspect_repository.py` becoming the public `view_of`, so that the tutor and
the repo state panel read one repository one way. Everything else under `src/`
is new files, one property on `AttemptPolicy`, one on `Services`, a command, a
route and a sentence in the interview banner.

**What the menu's *Touches* column would have said, had this been on it:** a
domain property, an application use case and a view model, two interface
surfaces. That is what it was. The cheapness is not luck — it is Phase 1's
decision to keep a full event log and Phase 8's to inspect through the grading
port, both made for other reasons, paying for a feature neither anticipated.

**Six findings, all in §16.** The author's notes had never been shown anywhere;
the reference solution was already unreachable from the application layer; a
pipe on Windows would have raised on 96 of the exercises; the first version of
the test for that could not fail; the copy button's promise depends on window
focus; and a pasted transcript carries the path of the fixture's remote.

### Phase 19 — The MCP server: the same attempt, fetched instead of pasted · **1 session**

The seventh stretch item and the second half of Phase 18's request: *is there a
more advanced way to do this?* A pasted bundle is a snapshot, stale as soon as
another command runs. An MCP client — Claude Desktop, Claude Code — can start a
local server and call tools on it, so the model fetches the attempt itself.

**The prediction, written before the phase:** a third driving adapter over the
use cases Phase 18 had just built, costing one interface package and one
optional dependency, and touching nothing under `application/` or `domain/`
except a second read. **It held, with two asterisks**, and both are in the
exit table: the read turned out to need a guard nobody had needed before, and
the dependency had changed its API since the plan was written.

**Commits** — six, in dependency order
1. `build: add the mcp sdk as an optional extra`
2. `feat(application): read one file from an attempt through the read-only ports`
3. `feat(mcp): serve the tutor context to an mcp client over stdio`
4. `feat(cli): start the mcp server with practice mcp`
5. `test(e2e): ask a tutor over a real protocol session, and prove it wrote nothing`
6. `docs: close phase 19 with ADR 0024`

The dependency is first and alone because it was the phase's one real risk, and
a commit list is a dependency order: nothing after it can be type-checked
without it.

**Exit criteria.**

| Criterion | Met by |
|---|---|
| A client over real stdio completes a handshake and reads an attempt | `tests/e2e/test_ask_a_tutor_over_mcp.py`, with `practice mcp` as a subprocess |
| The answer is live across two processes | the same test: a command run in the test's process is in the server's next answer, with the commit it stranded |
| Every tool reads, and says so | `test_it_advertises_three_tools_and_every_one_is_marked_read_only`, which fails a fourth tool by name |
| No tool can run a command | `test_no_tool_takes_anything_that_could_be_a_command`, and `Services.read_attempt_file` holding no route to `Workspace.run` |
| Tool calls change nothing | the last test in `tests/integration/test_mcp_server.py`, after the rest of the file has called tools against the same two attempts; and the e2e test's final assertions |
| A revision chosen by a model cannot become an option to git | `test_a_revision_beginning_with_a_hyphen_is_refused`, `test_what_reaches_the_repository_is_a_hash_and_never_the_callers_string`, and `test_a_revision_that_is_really_an_option_never_reaches_git` against real git |
| A kata's hidden suite is refused through a fourth surface | `test_a_katas_hidden_suite_is_refused_and_its_own_file_is_not`, on a provisioned workspace where the suite really is on disk |
| The spoiler boundary and the interview refusal are inherited, not restated | `test_get_context_is_the_attempt_read_from_the_real_repository`, `test_an_open_interview_is_refused_by_every_tool_that_reads_it` |
| The SDK is optional: every other command loads without it | `tests/integration/test_cli_mcp.py`, with the SDK removed from the import system |
| Only one package imports the SDK, and it cannot reach an adapter or a process | three new rules in `tests/unit/test_architecture.py`, each broken on purpose to see it fail |

**What changed that already existed:** `composition.py` and
`use_cases/__init__.py` gained an entry each, `main.py` gained a command, and
`test_architecture.py` gained a name in `IO_MODULES` and three tests. Nothing
under `adapters/` moved, and that includes the adapter with the hazard in it —
see the third finding.

**Five findings, all in §16.** "Read-only port" was a claim about a contract
rather than an implementation; the plan's "read-only git commands" tool was the
wrong shape and `RepoQuery` was the right one already; the SDK's API had turned
over a major version; the first test of the missing-extra refusal was fitted to
its own mock; and the tutor-is-invisible-to-the-grade hole from Phase 18 has
lost the argument that excused it.

### Phase 20 — Tracks, a Next button, and done-and-when · **1 session**

**Goal:** a solver can pick a route through the library, see which steps they
have passed and when, and go from one finished attempt to the next without
visiting a list. Started from a report that the tool had no memory; it had, and
could not be asked ([ADR 0025](adr/0025-tracks-are-a-second-manifest.md)).

| Exit criterion | Met by |
|---|---|
| Every list says whether and when an exercise was passed, without a schedule grade | `tests/web/test_tracks.py::test_browse_says_when_an_exercise_was_passed`, `::test_the_queue_no_longer_calls_a_solved_exercise_new`; `tests/unit/application/test_tracks.py::test_an_exercise_solved_and_never_scheduled_is_still_recalled` |
| A finished attempt offers the next step before any grade is pressed | `tests/web/test_tracks.py::test_the_next_step_is_there_before_any_schedule_grade_is_pressed` |
| Next after a failure is the step after, not the same one | `tests/unit/application/test_tracks.py::test_after_a_failure_comes_the_following_step_and_not_the_same_one` |
| The track is carried from start to Next with nothing stored | the *carrying the track* group in `tests/web/test_tracks.py` |
| A track's order cannot contradict the curriculum's dependencies | `tests/integration/content/test_tracks.py::test_a_track_may_not_reverse_two_exercises_inside_one_section`, and its two passing twins |
| The shipped tracks are what they are called | `tests/content/test_library.py::test_the_blind_75_is_the_seventy_five`, `::test_a_track_named_for_a_kind_misses_nothing_of_that_kind`, `::test_no_track_offers_a_lesson_before_its_premise` |
| A pack carries its tracks, narrowed | `tests/integration/content/test_tracks.py::test_an_installed_pack_validates_and_offers_its_tracks` |

### Phase 21 — Statements you can check, and the interviewer's follow-up · **2 sessions**

**Goal:** every kata states its bounds and shows examples a solver can trust,
on a tab of their own; and a problem can carry variants that are picked or
drawn at random. Two requests from using the library, taken together because
the second is written in the first one's format
([ADR 0027](adr/0027-examples-are-source-run-against-the-reference.md),
[ADR 0028](adr/0028-a-variant-is-a-whole-exercise-offered-under-its-base.md)).

| Exit criterion | Met by |
|---|---|
| Every kata states its constraints and shows more than one example | `tests/content/test_katas.py::test_it_states_its_constraints`, `::test_it_shows_more_than_one_example` |
| Every example on the page gives the output it shows | `tests/content/test_katas.py::test_its_examples_give_the_output_they_show` |
| The workbench draws a Prompt tab and an Examples tab for a kata, and neither for the other kinds | `tests/web/test_statement.py` |
| The terminal and the tutor are shown the whole statement | `tests/unit/domain/test_exercise.py::test_the_statement_of_a_kata_carries_its_constraints_and_examples`, `tests/unit/application/test_export_tutor_context.py::test_a_katas_task_includes_its_constraints_and_its_examples` |
| A variant is loaded, reachable by id and under its base, and never listed | `tests/integration/content/test_variants.py` (the repository group) |
| A variant must vary a real, standard exercise of its own kind | `tests/integration/content/test_variants.py` (the validation group) |
| A choice resolves to the standard version, a named variant, or a draw over all of them | `tests/unit/application/test_choose_version.py` |
| The Start control offers the versions; the workbench says which came up | `tests/web/test_variants.py` |
| `practice start --variant` does the same from a terminal | `tests/integration/test_cli_lifecycle.py` (the variants group) |
| A variant is held to everything a kata is | `tests/content/test_variants.py`, which imports `test_katas.py`'s tests |
| A variant is not its base listed twice | `tests/content/test_variants.py::test_its_base_solution_does_not_pass_it` |
| A variant comes due for review once attempted and is never offered unprompted | `tests/unit/application/test_review.py::TestReviewQueueAndVariants` |

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
| [0007](adr/0007-htmx-over-a-single-page-app.md) | HTMX and server-rendered fragments, not a single-page app | accepted |
| [0008](adr/0008-sm2-first-with-fsrs-behind-a-port.md) | SM-2 first, with FSRS behind the same port | accepted |
| [0009](adr/0009-ship-our-own-prompts.md) | Ship our own prompts; never redistribute problem text | accepted |
| [0010](adr/0010-codemirror-5-over-6.md) | CodeMirror 5 over 6, to avoid an npm build step | accepted |
| [0011](adr/0011-reference-solutions-are-command-lists.md) | Reference solutions are command lists, not shell scripts | accepted |
| [0012](adr/0012-inspect-the-repository-through-the-grading-port.md) | The repo state panel reads through the grading port, not a second git path | accepted |
| [0013](adr/0013-grade-on-save-is-a-preview.md) | Grade-on-save is a preview that persists nothing | accepted |
| [0014](adr/0014-a-hand-ordered-curriculum-manifest.md) | A hand-ordered curriculum manifest, not a prerequisite graph | accepted |
| [0015](adr/0015-verify-on-the-working-tree-not-every-commit.md) | Verify on the working tree, not on every commit | accepted |
| [0016](adr/0016-a-generated-demo-not-a-recorded-one.md) | The demo is generated from captured output, not recorded | accepted |
| [0017](adr/0017-a-front-door-separate-from-the-server.md) | A front door (`practice up`) separate from the server | accepted |
| [0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md) | FSRS as a second scheduler, not a replacement | accepted |
| [0019](adr/0019-sql-drills-as-a-third-exercise-kind.md) | SQL drills as a third exercise kind | accepted |
| [0020](adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md) | Interview mode withdraws affordances it cannot contain | accepted |
| [0021](adr/0021-content-packs-install-rather-than-mount.md) | A content pack is installed to a directory, not mounted as a library | accepted |
| [0022](adr/0022-counter-examples-are-run-against-the-bug-they-name.md) | Counter-examples are run against the bug they name | accepted |
| [0023](adr/0023-the-tutor-context-is-what-the-solver-has-seen.md) | The tutor context is a projection of what the solver has already seen | accepted |
| [0024](adr/0024-an-mcp-server-that-can-only-read.md) | An MCP server over stdio that can only read, on the SDK as an optional extra | accepted |
| [0025](adr/0025-tracks-are-a-second-manifest.md) | Tracks are a second manifest, read off the attempt log and carried in the URL | accepted |
| [0026](adr/0026-the-current-attempt-is-a-mark-the-solver-leaves.md) | The current attempt is a mark the solver leaves, not something a tutor infers | accepted |
| [0027](adr/0027-examples-are-source-run-against-the-reference.md) | A kata's examples are source, and every one is run against the reference | accepted |
| [0028](adr/0028-a-variant-is-a-whole-exercise-offered-under-its-base.md) | A variant is a whole exercise, offered under the one it varies | accepted |

---

## 13. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Windows subprocess/path bugs | **High** | Windows in CI from Phase 0; argv lists only; sandbox tackled in Phase 3 while cheap to change; 6 sessions budgeted, not 4 |
| Non-deterministic fixture SHAs | Medium | The full pinned set in §6.1 — identity, dates, `fileMode`, `autocrlf`, `eol`, `defaultBranch` — verified against `content/fixtures.lock` on both platforms |
| Assertions too loose to tell right from wrong | **High** | Mandatory `naive.cmds` counter-examples that CI requires to fail, replayed through the real policy |
| Reference solutions validated through a path users cannot use | Medium | §5.3 — solutions are command lists replayed through `RunScenarioCommand`, never shell scripts |
| Content authoring stalls | **High — retired in Phase 11** | This was the real failure mode and it did not happen: 51 exercises authored, 54 in the library. Content-as-data plus Phase 2 proving the loop with three exercises before any UI existed. What it cost was a fortnight, and what made it survivable was the content suite catching five wrong counter-example declarations and three wrong expected values before any of them shipped |
| Scope creep into SQL/k8s/system design | High | Phase 13 parked these. SQL was unparked in Phase 14 on one condition: it had to be an *exercise kind*, not a second product. It is — `sqlite3` from the standard library, no service, no network, and `adapters/sql/` never touches the application's own database (ADR 0019). k8s and system design stay parked, and the test to apply is the same one: can it be graded offline, on both platforms, from declarative assertions? |
| Over-abstracting for the interview story | Medium — **exercised in Phase 11** | Every port must have ≥ 2 real or test implementations, or it gets deleted. The rule was applied to two *assertions* rather than a port: `reflog_contains` and `command_count` shipped flagged as unproven in Phase 5 and were deleted once 24 scenarios wanted neither, taking `RepoQuery.reflog` with them |
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
  The better half of the answer is what those two *still* miss: under DNS
  rebinding both headers are `same-origin` and both are telling the truth, so a
  `Host` allowlist is the third guard — and the fact that it has to cover reads
  as well as writes is the part that shows you have thought about it rather than
  copied it.

---

## 15. Open questions

Not blockers — decide when the phase arrives.

1. **Merge-conflict scenarios** need a mid-attempt editing surface (resolve the
   conflict, then continue). The virtual `write` command takes content as a
   single argv element, so it cannot express multi-line file content or
   embedded quotes — which means the CodeMirror pane is probably *required*
   here, not optional. Decide in Phase 8; the alternative is a
   `resolve <path>` affordance that opens the conflicted file in the editor.

   **Half-answered by Phase 7: the pane exists.** CodeMirror is vendored, wired
   over a textarea and reading its language from the exercise
   ([ADR 0010](adr/0010-codemirror-5-over-6.md)), so what is left is the
   affordance rather than the widget — which is the cheaper half. The same is
   true of question 2's plan file.
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
   CodeMirror pane solves that, both questions get easier at once, which is the
   right order to take them in. **The pane landed in Phase 7**, one phase earlier
   than this paragraph assumed, so that discount is already available.
3. **Kata languages beyond Python.** The runner is already behind a port, so
   adding TypeScript means a `vitest` adapter. Worth it only if you interview
   in TS.

   **Phase 14 tested the front half of this question without meaning to.** A SQL
   drill needs a second CodeMirror mode, which is the same vendored-asset work a
   second kata language needs — and `vendor.py` had predicted it costs "a second
   line here and nothing else". The line was right: `verify`, the offline grep,
   the asset route and the hash test were all untouched, and
   `tools/vendor_assets.py` behaved exactly as designed (fetch, refuse the
   placeholder hash, print the line to paste). What the prediction missed is that
   `workbench.html` had the Python mode *file* hardcoded in its script tag, so
   the page would have served a Python tokenizer and then asked CodeMirror for a
   mode it had not loaded — failing silently, by degrading to a plain textarea.
   `vendor.mode_file` is the fix. **So a second kata language is now one line in
   the manifest, one committed file, and a `language:` in the exercise** — and
   the runner adapter is the only remaining cost, which is the half this question
   was always about.
4. **Curriculum sequencing — answered in Phase 11 at fifty-four exercises, and
   the revisit found that "hand-ordered" had never actually happened.** The
   library's order was `sorted(ExerciseId)`, so it was ordered by spelling:
   `edit-distance` fifth, before `climbing-stairs`. `content/curriculum.yaml`
   now declares eleven tracks in order — nine, plus the two SQL runs Phase 14
   interleaved between them — and `validate_library` requires it to cover the
   library exactly ([ADR 0014](adr/0014-a-hand-ordered-curriculum-manifest.md)).

   **Phase 14 found the one place the manifest is now tight.** `start-here` is
   six exercises against a six-row dashboard queue, two of each kind, with no
   slack: a fourth exercise kind cannot be put on the first screen without
   taking something off it. That is a decision worth forcing rather than
   discovering, and
   `test_the_first_screen_of_the_curriculum_offers_every_kind` is what forces
   it.

   **Prerequisite-graph unlocking stays parked, and now for a product reason
   rather than a sequencing one.** It needs the attempt history as an input to
   the review queue rather than just the card store, and it changes the tool from
   advising to *gating* — a solver who wants `edit-distance` today should be able
   to have it. Revisit if `practice progress` ever shows that everybody fails X
   before Y and succeeds after, which is a measurable claim the attempt table
   already holds the data for.

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


**2026-10-02 — Phase 7 built: the web shell and the kata workbench.** Four
sessions budgeted, five commits. The phase where the second driving adapter
finally exists, and the §2 claim it was built to test — *if the core were secretly
coupled to HTTP, a second driving adapter wouldn't work* — holds in the direction
nobody had checked. **No use case changed, no grader changed, no adapter changed.**
What the web app added to the layers below it is one use case and one DTO, and
both exist for a reason the CLI genuinely does not have.

**That one addition is the finding worth keeping: a URL outlives the state it was
created for.** `practice submit` grades an attempt, prints a verdict and is done
with it, so nothing in six phases ever needed to *re-read* a finished attempt.
`/attempt/{id}` is a tab somebody left open across that submission, a bookmark, a
link from the dashboard — and it has to render either way. `ResumeAttempt` refuses
a finished attempt, correctly, because resuming one is not a thing that can
happen; bending it to cover this would have made it two use cases wearing one
name. `OpenWorkbench` is the second, and it differs from its neighbour in exactly
one case. The general form, which generalises past this project: **a request/response
adapter asks for reads that a command-line adapter never does, because a command
is over when it prints and a URL is not.**

**The §8.3 security pair does not cover DNS rebinding, and the reason is the
opposite of obvious.** The plan names two guards — bind to loopback, and reject a
mutating request whose `Origin` is not ours and whose `Sec-Fetch-Site` is not
`same-origin`. If `evil.example` resolves to 127.0.0.1, a page served from it
sends `Origin: http://evil.example` to a request whose own `Host` is
`evil.example`, so the two *agree*; and the browser reports
`Sec-Fetch-Site: same-origin`, truthfully, because as far as it is concerned they
are one origin. **Both named guards pass.** A `Host` allowlist is three lines and
is the only thing that sees it, which is also why it has to apply to reads: a
rebound page that can read our HTML can read an attempt's transcript out of it.
§8.3 and §14 both now say *two and a half guards*.

The related decision, recorded because the lenient version is what most localhost
tools ship: **a request that proves nothing is refused, including one that says
nothing at all.** Treating "no `Origin` and no `Sec-Fetch-Site`" as "not a
browser, so allow it" hands the entire guard to any browser that omits the header.
Browsers have sent `Origin` on every non-GET fetch for years, so strictness costs
a browser nothing; what it costs is `curl -X POST` one header, and there is a CLI
over the same use cases that needs no server at all.

**Five things found by running it, which is five for five across the phases that
have kept count.**

- **Starlette's `url_for` renders an *absolute* URL.** A layout written the
  documented way serves `http://127.0.0.1/static/app.css` on every page. The
  offline grep flagged it on its first run — it cannot tell that `http://` from a
  CDN's — and the deeper problem is that a page hardcoding the host it happened to
  be rendered for stops working the moment it is saved or opened under the other
  loopback spelling. The static prefix is a Jinja global and the links are
  root-relative.
- **`httpx2`, not `httpx`.** Starlette's `TestClient` warns on the latter, and
  this project's `filterwarnings = ["error"]` turns that warning into a
  *collection* error. The obvious dependency is the broken one here, which is
  exactly the sort of thing a lockfile comment is for.
- **`python-multipart` is a runtime dependency**, not a test one: FastAPI raises at
  request time without it, and the browse page starts an attempt with a form. Found
  by a test suite that went from green to 49 errors on one route being added — and
  worth noting that the failure was *not* at import time, so nothing static saw it.
- **`height: auto` plus `min-height` is wrong for CodeMirror.** It looks right
  until a short stub loads: the widget sizes to its eight lines, the min-height
  leaves empty panel underneath, and the horizontal scrollbar is drawn at the
  content edge above the dead space. A fixed height with the widget's own scrolling
  is what that wanted.
- **Grading needs an in-flight state.** It starts a pytest subprocess and takes a
  second or two, and a button that does not change reads as a button that did
  nothing — so the second click it invites gets refused by the aggregate, and the
  reward for impatience is an error message. The button disables itself and says
  `Grading…`.

**The vendoring rule had to be split in two, which the plan did not anticipate.**
§8.2 says the offline test greps every template and static file for `http://`. It
cannot: a minified library carries its own licence URL in a banner comment, so
grepping the vendored files would either condemn an asset that fetches nothing or
be weakened until it caught nothing. So **our files are grepped and theirs are
pinned by SHA-256** — and a third test asserts that every file under `static/`
falls into one of the two sets, because the failure mode of a split rule is a
category that appears between the halves and is checked by neither. The hash is
the stronger claim in any case: the grep says *this file names no remote host*,
and the hash says *this file is the one that was reviewed*. `.gitattributes` gained
`-text` on that directory for the same reason, and it is the one exception to the
LF rule above it — `text=auto` would normalize the bytes on a Windows checkout and
the verification would then pass on Linux and fail on Windows.

**One deliberate limitation, stated rather than hidden.** The workbench has no
draft persistence: closing the tab loses the editor buffer, because the only
`SolutionSaved` event is the one a submission writes. Adding an autosave endpoint
would put a write on a page load's sibling path, and the event log is read by the
§6.3 process assertions — so it is a decision about what counts as something the
solver *did*, not a missing feature to slip in. Phase 8 reopens it alongside hint
reveal, which has the same shape.

**The commit split was clean this time, and the known caveat did not fire.** All
four commits passed the cheap tier on their own, and the pre-push run found
nothing the cheap tier had missed — the first phase since the rule was written
where that is true. The reason is visible rather than lucky: this phase changed no
existing user-facing string. Every new message is in a file that did not exist
before, so the one shape the cheap tier cannot see had nothing to see.

The phase closed at **1,973 tests** — 111 more than Phase 6 — with `domain/` and
`application/` at **100%** statement and branch coverage against the 90% gate, on
1,364 statements and 258 branches. `practice validate` and `practice fixtures
--check` are unchanged and green, and `unproven_by_design` still names the same two
permanent caveats.

**2026-10-02 — Phase 8: the git scenario workbench.** The phase the whole project
was arranged to make possible, and the first one where the *rendering* of a
repository was the hard part rather than the reading of it.

**The decision worth the ADR is which repository the panel reads.** A
display-only git wrapper — `git status` as humans see it, `git branch -vv` —
would have been less code and no new port. It would also have put two readers of
one repository in the app, and the disagreement that matters is invisible:
`worktree_clean` ignores untracked files by design (§6.5), so a panel built on raw
`git status` reads as dirty exactly where the verdict reads as clean, and the
solver has no way to tell which one lied. So inspection goes through `RepoQuery`,
`RepoQueryFactory` moves from a protocol inside `adapters/git/grader.py` to a port
in `domain/ports.py`, and `Services` holds one factory that both the grader and
the panel are built from. ADR 0012, with the rejected alternatives.

**The port moved because a protocol in an adapter is reachable only by that
adapter's collaborators** — true for three phases, and false the moment a second
caller appeared. Worth recording as a pattern rather than as an incident: §13's
rule is that a port needs two implementations to earn its place, and the natural
consequence is that a protocol starts life next to its only user and is promoted
when the second arrives. `RepoQueryFactory` had two implementations from day one
(`GitRepoQuery` and a test factory) and still belonged in the adapter until Phase 8.

**Two defects in the graph layout, both caught while reasoning through the merge
case rather than by running anything, and both invisible on the shapes a fixture
mostly has.** Building an edge from a lane *reservation*
rather than from the finished row sends it to a column the parent is not drawn in —
two children can each reserve a lane for one parent, and the parent is drawn in
exactly one of them. And a lane left reserved after its commit is claimed elsewhere
is never freed, so every later branch starts a column further right. Neither shows
on a linear history, which is what the shipped fixtures have, so neither would have
been found by driving the app — the only thing that would have caught them is the
thing that did: writing down what a merge means before writing the loop. Both now
have named tests, and the fix for the first is a second pass that resolves every
edge from the finished rows, where the only endpoints available are positions
something is actually drawn at.

**The graph reads every ref, not HEAD.** Found by using it. A drawing taken from
`log("HEAD")` is correct and useless at the moment it matters most: after
`git reset --hard HEAD~1` the commit still on `origin/main` is unreachable from
HEAD, so the graph would have gone quiet about exactly what the solver just did.
`merge_logs` asks for one log per distinct ref tip and merges them with Kahn's
algorithm, tiebroken on input position, which gives a deterministic order in which
every commit precedes its own parents — the property `lay_out` needs. Commit dates
would be git's own tiebreak and `CommitInfo` does not carry one; adding a field to a
port value object for one renderer was the wrong trade, and the difference only
shows between commits neither of which can reach the other.

**"Text lanes first, then the SVG renderer" was one deliverable, not two.** §11's
sequencing is risk management and the risk is the lane model, which is proved by
its own unit tests with no renderer involved. Once that was green a text rendering
would have established nothing the SVG does not, and shipping both would have meant
two drawings of one model. The §10 sketch of `adapters/git/graph.py` stays absent
for the reason Phase 5 gave; the Phase 8 graph module is a different thing in a
different layer — a pure view model in `application/`, where the coverage gate
covers it and where `domain/` would have been wrong, because a lane number is not a
rule the product can be right or wrong about.

**The draft-persistence question Phase 7 left open is answered, and the answer is
no.** Hint reveal has the same shape on the surface — both are a write on a path
that looks like display — and they come apart on the question the event log asks:
*is this something the solver did in the exercise?* Revealing a hint is, and Phase
9's grade suggestion will read it, which is why `RevealHint` is a use case and the
reveal is persisted. An editor autosave is not; it is a keystroke, and a log full of
them would make every §6.3 process assertion learn to ignore a kind of entry. The
workbench still loses the buffer when the tab closes, now on purpose rather than
pending.

**Three findings from looking at the page, none of which a test would have caught.**
`:empty::after` can never place a placeholder inside a `for` loop, because the loop
leaves whitespace in the element — it is a real `<li>` hidden by `:not(:last-child)`
once htmx appends past it. The prompt column needed widening before the flagship
fixture's own prose stopped wrapping mid-sentence at three columns. And the first
draft put `hx-confirm` on the reveal-a-hint button, which is defensible on paper and
awful in use: a blocking native dialog in front of something done four times an
attempt. The control says "recorded on the attempt" beside it instead; `hx-confirm`
stays on Submit, which cannot be undone.

**The commit split needed no additions this time** — unlike Phases 6 and 7, the
list in §11 was also the list that shipped. What it needed was a repair: commit
2 failed `ruff` on its own, because a lint fix for a test it introduced had been
made in the working tree and swept into commit 3. The cheap tier caught it, the
amend-and-rebase cost two minutes, and it is the mirror image of the caveat §11
already records — not a defect attributed to the wrong commit, but a *fix*
attributed to the wrong one.

The phase closed at **2,115 tests** — 142 more than Phase 7 — with `domain/` and
`application/` at **100%** statement and branch coverage against the 90% gate, on
1,588 statements and 328 branches — 224 statements and 70 branches more than Phase
7 covered, almost all of them in three places: the inspection use case, the lane
layout, and the DTOs those two feed. `practice validate` reports three exercises
valid and `practice fixtures --check` matches both fixtures against
`fixtures.lock`.

**2026-10-02 — Phase 9: spaced repetition and progress. The MVP is complete.**
Three sessions budgeted and the work landed in that range; the surprises were
all in the shape of the phase rather than in its difficulty.

**The commit list was missing the commit that makes the phase work.** §11
sketched four — scheduler, queue, dashboard, charts — and none of them writes a
card. Without a surface that grades a review the due queue is empty forever and
the exit criterion is unmeetable, so the real list is seven. Worth recording as a
category rather than as an oversight: Phases 6 and 7 needed additions too, and
the shape is always the same one — a plan written from the *model* outward
describes every piece of state and forgets the gesture that creates it.

**The `Scheduler` port's signature was wrong in §4.6, and the property test is
what said so.** `next_card(card, grade, today: date)` cannot produce the
`last_reviewed_at` the card carries, and §9.7's fourth property — *`due_on` is
always after `last_reviewed_at`* — is stated as a property *of the scheduler*.
Either the scheduler returns a card with a stale review time for a use case to
patch, splitting one card's construction across two places, or the port takes
the instant. It takes the instant; `today` is `now.date()`.

**The clamp §9.7 names was hiding two more stalls.** The plan predicts that at
the 1.3 ease floor `round(1 × 1.3) == 1`, so a naive multiply leaves a one-day
interval where it was and the monotonicity property fails. True, and writing the
property first also surfaced that `HARD` multiplies by 1.2 whatever the ease, so
*any* interval under two and a half days rounds back to itself, and that Python's
round-half-even (`round(2.5) == 2`) would add a third. One clamp on the shared
return covers all three, which is the argument for putting it there rather than
inside the `GOOD` branch — and is a small vindication of §9.7's "write the test
first and watch it catch this".

**A suggestion is not a schedule, and keeping them apart is the phase's main
design decision.** The tool proposes a grade from three readings it has and the
solver does not — the verdict, the hints revealed, the time against the author's
estimate — and then waits to be pressed. Applying it automatically would make the
queue self-filling and an override impossible to honour, because a card is
replaced rather than versioned (Phase 6) and a correction would land on a
schedule already moved. The rule is three penalties against a ceiling: a pass
never suggests `AGAIN`, because `AGAIN` means *you did not know this* and someone
whose end state satisfied every required check did. It lives in `domain/` and not
behind the port, because FSRS would want it unchanged.

**`RevealHint` being a use case since Phase 8 paid off exactly as predicted.**
That commit's message argued the reveal is persisted because "Phase 9's grade
suggestion reads that record". It does, and the sentence the schedule block shows
— *passed, but 1 hint revealed* — is the whole of why the log was worth keeping.

**Two port additions, each with a reason the other does not cover.**
`ReviewRepository.cards()` is not a looser `due_on`: the queue is a join against
the whole library, and an exercise with no card is the most common due item there
is, so a method returning the due subset can never report one. `due_on` keeps its
place because its ordering *is* the queue's. `AttemptRepository.completed()` is
`active()`'s counterpart, and it is the query `sqlite/attempts.py` predicted in
Phase 6 — "the shape that stops being free the first time a progress page asks
for a hundred attempts". It is two statements rather than N+1 for that reason;
the honest limit is that it loads whole aggregates, which is fine at hundreds of
rows and wants a projection rather than a narrower query if it ever is not.

**Three defects found by looking at the page, and one of them is the worst kind.**
The default button in this app is an accent *fill* with background-coloured text,
so marking the suggested grade by accenting its border and label painted accent
on accent and shipped a button with no words on it — four controls, one blank,
and every fragment assertion green. The tests could see `class="grade suggested"`
and could not see that it rendered invisible; nothing short of a screenshot
would have. (Also: idle ticks drawn in the bar colour made a 30-day window with
one attempt read as a dashed chart rather than as a month off, and the history
said "0 min" for every attempt under a minute, which is most of them.)

**Writing the e2e found that two pages' sentences were unassertable.** A Jinja
block that wraps the source wraps the output, so the streak line a person reads
is not a line a test can match; the web tests had been checking fragments short
enough to fall inside one line and had not noticed. `partials/verdict.html`
already knew this and said so in a comment — the finding is that the comment was
load-bearing and nobody had carried it to the next template.

**The Phase 2 tripwire mechanism worked a second time.** The dashboard carried a
section saying due-today and a streak were "phase 9", with a test asserting that
sentence was *present*, so that landing the phase would break the build and force
someone to delete the promise. It broke. The inverse assertion is what is left.

**The phase is web-only, deliberately, and it is the first one that is.** Nothing
in the CLI schedules a review or prints a queue, so a solver who only ever runs
`practice submit` builds no history. That is defensible — §8.4 puts due-today,
the streak and the weakest tags on *pages*, and the suggestion is a control with
four buttons that a terminal would have to prompt for, which would block
`practice solve` in CI the way an interactive resume prompt would have (Phase 6)
— but it is worth saying out loud rather than discovering. The cheap half, a
`practice due` that prints the queue, is one command over `ReviewQueue` and has
no new ports behind it; the expensive half is the grade, and it is the half that
would have to answer what a non-interactive invocation does.

ADR 0008, whose number §12 reserved in the original plan, records SM-2 over FSRS
and the three constraints that decide it — no review log to fit against, a
scheduler being the easiest thing in the system to get wrong quietly, and a
library of tens rather than thousands of cards. Its most useful paragraph is the
cost: the card keeps no history, so every day the tool runs without one is a day
of evidence that cannot be recovered, and the table being easy to add later is
not the same as the data being recoverable.

The phase closed at **2,277 tests** — 162 more than Phase 8 — with `domain/` and
`application/` at **100%** statement and branch coverage against the 90% gate,
on 1,892 statements and 366 branches: 304 statements and 38 branches more than
Phase 8 covered, almost all of them in four places — the scheduler, the
suggestion rule, the progress summary and the three new DTOs. `practice validate`
reports three exercises valid and `practice fixtures --check` matches both
fixtures against `fixtures.lock`.

**2026-10-02 — Phase 10: own-editor mode.** Two sessions budgeted, two commits
sketched, three written — the third being this entry and ADR 0013. The phase
reads as two features and is really one finding and one decision.

**The finding is that there was nothing to scaffold.** The first commit is called
"file mode scaffolding" because the plan called it that, and the plan was wrong
in a cheap direction: `SubprocessSandboxProvisioner` has copied a kata's stub
into `<workspace>/repo/<stub>` since Phase 3, and `OpenWorkbench` has seeded the
browser editor by reading it from there since Phase 7. **The stub already was the
working copy.** The first draft of this phase created a second file for the
solver to edit, which is one file too many: the page and the editor would have
shown different things and whichever was submitted the other would have been
silently discarded. What was actually missing was the *path* — so the commit
added `Workspace.resolve` to the port (promoting a method
`SubprocessWorkspace` already had) and gave it two callers, and the CLI's whole
share of the phase was one line: `_next_step` now names the file instead of
saying `--source FILE`. Which means **the terminal has had own-editor mode all
along** and nobody could find the file.

**The decision is ADR 0013: a save is a preview that persists nothing.** The
obvious implementation — call `SubmitSolution` on every save — cannot work, and
not for a fixable reason: submission completes the attempt and disposes of the
workspace holding the file being edited, so the first Ctrl+S would end the
exercise and delete the directory. The next idea, appending a `SolutionSaved`
event per save, works and is worse, and Phase 8 had already settled the
principle for the browser editor: a save is a keystroke, not something the
solver *did in the exercise*. Three things read that log as a record of
deliberate acts — the §6.3 process assertions, the Phase 9 grade suggestion, and
`latest_source` — and all three would have grown an exception. So
`WatchSolutionFile` loads the attempt, hands it the source **in memory**, grades
that aggregate and throws it away. The `SolutionSaved` event lives for one
grading pass, which is exactly as long as `Grader.grade`'s contract needs it
(*a verdict is derived from a source the attempt remembers*), and the stored log
is untouched. The property is held by a test that counts the events after three
saves and by the e2e, which asserts one `SolutionSaved` for one submission.

**Grading acquired a concurrency problem it had never had, and the port addition
is what found it.** A submission cannot collide with itself — the aggregate
refuses a second one — so until now nothing could run two grading passes over
one workspace. Grade-on-save can immediately: §8.1 explicitly supports an attempt
being open in another tab, and two tabs are two SSE streams, each writing
`solution.py` and reading `report.json` in the same directory. Interleaved, the
second overwrites the source the first is about to run and `report.json` comes
back describing somebody else's code — a *wrong verdict on a completed attempt*,
which is the worst outcome this system has. Answered in `PytestKataRunner`, which
is the module whose own docstring already called those files "this module's
contract with the subprocess": the write-run-read sequence is under one instance
lock, and the composition root builds exactly one runner, which is what makes an
instance lock enough. A submission may now wait out a preview, bounded by the
exercise's time limit. That is the right price.

**Three Windows findings, all from running it rather than reasoning about it.**

- **A bare `code` cannot be started.** `Popen(["code", path])` raises
  `FileNotFoundError [WinError 2]`, because `CreateProcess` searches `PATH` and
  does not apply `PATHEXT` — and the file VS Code installs is `code.CMD`.
  `shutil.which` does apply it, and `Popen` of the resolved `.CMD` works. The
  resolution goes through `execution.resolve_program`, which is the one function
  in the package that already knew this, from the other direction.
- **`shlex.split(posix=False)` keeps the quote characters in the token.** Needed
  on Windows, because POSIX mode treats a backslash as an escape and turns
  `C:\Tools\npp.exe` into `C:Toolsnpp.exe`. But non-POSIX mode produced a
  program name of `'"C:\...\python.exe"'`, quotes included, which resolved to
  nothing. One matching pair stripped by hand is the whole fix, and the case it
  is for is an editor under `C:\Program Files`, which is where editors are.
- **A fire-and-forget `Popen` fails this test suite, and it is right to.**
  `Popen.__del__` emits a `ResourceWarning` when it is collected with a live
  child, and `filterwarnings = ["error"]` turns that into a failing test —
  correctly, because an abandoned child is also a zombie on POSIX, since nothing
  reaps it. So the launcher keeps a reference to every process it started and
  polls them on the way past, which reaps the exited ones and keeps the live ones
  from being collected. The warning is right about production, where a server
  holds its launcher for its whole life, and wrong about a test, whose launcher
  dies at the end of the function — so the test waits, through a fixture that
  exists to say exactly that.

**The watcher watches the directory, not the file, and that is not an
optimisation.** Editors do not write files, they replace them: VS Code, vim and
anything else that saves atomically write a temporary file and rename it over the
target, so the inode a file watch was given stops being the file the solver is
editing after the first save. A file watch sees one modification and then nothing
ever again, which is the version of this bug that looks like it works. The filter
is positive and names the one file, because the grading pass writes five others
into the same directory — so a watch that reported everything would re-grade on
its own output, forever, as fast as pytest can start. Excluding the known five
would be the same rule written the fragile way round.

**`watchfiles` is now in the architecture test's I/O module set**, and it is the
first third-party name in it. A file watcher is I/O in the same sense a socket
is, and the `FileWatcher` port exists so that a use case wanting to know about a
save asks for one rather than importing one. Without the line in the test, that
would have been a paragraph in a docstring.

**The periodic tick turned out to be load-bearing, which the first draft of the
port did not have.** `FileWatcher` yields `False` as well as `True`, and the
`False` is how the web layer discovers that the browser holding a stream open has
gone: without it the generator sits in `awatch` forever, and every closed tab
leaves a watcher running until the server stops. The tick is also what the ping
is written on, and writing is what fails on a dead socket — so the keepalive is
the mechanism, not the courtesy. The matching half is `contextlib.aclosing`
around the loop: returning from the generator on a disconnect leaves the one
underneath it to be garbage collected, and the watch runs for as long as that
takes — which would have undone the reason the tick exists in the first place.
Both use cases' generators are therefore typed as `AsyncGenerator` rather than
`AsyncIterator`, which is the narrower and truer claim: something holding a live
watch should be closeable.

**No fifth vendored asset.** htmx 2 moved SSE out of the core into
`htmx-ext-sse`, so the attribute form would have meant another file to download,
hash-pin, review and keep current (§8.2) for one panel on one page. The workbench
has hand-wired its own submission in a `<script>` since Phase 7, because
CodeMirror forced it, so the honest comparison was four `addEventListener` calls
against a new third-party dependency. The four lines won.

**Two smaller things worth writing down.**

- **A refusal on an SSE endpoint has to be a 200.** `EventSource` reconnects on
  its own after a failed response, forever, with no way to decline — so a 404
  would turn one unopenable attempt into a request every few seconds for as long
  as the tab is open. The stream opens, says what is wrong in a `problem` event,
  says `done`, and the page closes it. This is the same "refusals are 200"
  conclusion the htmx routes reached, for a completely different reason.
- **A preview of a kata with a complexity expectation can never be a clean
  `PASS`.** Found by the e2e, asserting the wrong outcome word. Declaring the
  cost is part of *submitting*, so every draft carries the `not declared`
  advisory. Accurate, and arguably a useful standing reminder — but it means the
  outcome word changes at submission time for a solver who does declare, and
  that is better stated than discovered.

**Universal newlines make the CRLF round trip safe, by accident of Phase 3.**
The exit criterion is "save in VS Code", on Windows, where an editor may well
write CRLF. `Workspace.read_file` uses `read_text`, whose universal-newline
translation turns `\r\n` into `\n` on the way in; `write_file` passes
`newline=""` so LF survives on the way out. So a CRLF save crosses the SSE
stream as LF and submits as LF, and the blob the grader sees is the same one on
both platforms — which is the §6.1 determinism guarantee holding somewhere
nobody wrote it down for.

**The fake watcher is a queue, and a test that appends to it on every draft never
ends.** Written as a list iterated in place, which is almost right: appending
from inside the loop is the sequence a solver actually produces (save, read the
verdict, save something different), and the first test to use it appended
unconditionally. The symptom is a *unit* test that hangs rather than fails, which
is the worst shape a test failure has. The fake now pops from the front and its
docstring names the trap.

**Double quotes inside a `-c` payload split a command in half, twice.** Both the
integration suite's stand-in editor and the e2e's hit it: the script is passed as
one double-quoted argument, and a double quote in the middle of it closes that
quote in `shlex`'s eyes. The integration one switched to single quotes inside;
the e2e's payload is the kata solution, which contains
`ValueError("no pair ...")`, so it is base64 and decoded in the script. Worth the
note because the failure is silent — the process starts, the launch reports
success, and the only symptom is a timeout somewhere downstream.

The phase closed at **2,348 tests** — 71 more than Phase 9 — with `domain/` and
`application/` at **100%** statement and branch coverage against the 90% gate,
on 1,996 statements and 386 branches: 104 statements and 20 branches more than
Phase 9 covered, almost all of them in the two new use cases and the two new
DTOs. `practice validate` reports three exercises valid and
`practice fixtures --check` matches both fixtures against `fixtures.lock`.

**The cheap tier's known caveat did not fire, and this time it was checked
rather than lucky.** The phase changed exactly one existing user-facing string —
`_next_step`'s kata branch, which said `--source FILE` and now names the file —
so the one defect that tier cannot see had somewhere to hide. `grep -rn` found
the only test asserting on `--source FILE`, and it is about a different message
(`submit`'s refusal when a kata is submitted without one), which is unchanged.
Both commits passed the cheap tier on their own and the pre-push run found
nothing new, which is the second phase in a row where that is true.

**2026-10-03 — Phase 11: the content build-out. Fifty-four exercises.**
Eight-plus sessions budgeted, seven commits sketched, thirteen written. The plan
said "pure authoring, no code changes — which is the payoff of §5", and it was
nearly right: four of the thirteen commits touch code — three of them the content
finding a gap in the engine it was written against rather than a change of
direction, and the fourth a guard test for a property of the *library* that no
single exercise could carry. That is the phase's shape, and it is the opposite of the
one the plan feared — the risk register had "content authoring stalls" at
**high**, and what actually happened is that authoring kept finding bugs in the
grader.

**The §5 bet held, with one exception that is now written down.** 51 exercises
were added as data — 24 git scenarios, 30 katas, 283 new files under `content/` —
with no change to the loader, the graders or either driving adapter. The
exception is `reference_failing_commands`, which *is* a schema field, and the
reason it exists is the most useful finding in the phase.

**Three findings that cost code.**

- **A conflict scenario's answer begins with a command that fails.** `git merge`
  on a conflict exits 1, so does a `git rebase` that stops partway, and so does a
  push rejected as non-fast-forward. `test_its_reference_solution_replays_without_errors`
  required *every* reference line to succeed, which made the single
  most-requested git skill unauthorable — and the strictness was right, because
  it catches a mistyped flag and names the line. §15 question 1 had parked
  merge-conflict scenarios for this phase expecting the problem to be the editing
  surface; the editing surface turned out to be fine (the virtual `write` takes
  one argument per line) and the exit code was the blocker. Resolved by
  **counting** rather than flagging: `reference_failing_commands: 1`, and the
  suite holds the reference to exactly that number. A boolean "this reference may
  fail" was rejected because it excuses every *other* failure in the same file,
  which is precisely the defect the assertion exists to catch. Three scenarios
  use it.
- **`@{u}` is a git revision and the content suite thought it was an alias.**
  `publish-a-branch-for-review` asserts that a branch has an upstream, and
  `ref_points_at {ref: "@{u}", target: HEAD}` is the only way the vocabulary can
  say so — `@{u}` resolves to nothing when no upstream is configured, so it is a
  check on `.git/config` rather than on the remote. It graded correctly and failed
  a test about *fixture aliases*, because that test treated any parameter starting
  with `@` as one while the domain's rule is narrower by design
  (`^@([A-Za-z][A-Za-z0-9_-]*)$`, so `@c2` can never collide with git's own `@`
  syntax — §6.5). Two definitions of alias syntax, one `startswith` apart.
  `alias_name` is now exported from `domain/checks/evaluation.py` and both call it.
- **The two unproven assertions were deleted, and the flag is why it happened.**
  `reflog_contains` and `command_count` shipped in Phase 5 registered,
  implemented, and labelled in three docstrings as deleted-rather-than-carried if
  no Phase 11 exercise found a use (§13). Twenty-four scenarios later — eight
  about recovery, three turning entirely on the reflog — neither was wanted once.
  `reflog_contains` is vacuously true wherever the fixture created the entry
  (every attempt at `recover-a-lost-commit` passes `{pattern: "^reset:"}`,
  including one that ran no commands) and otherwise grades *how* a solver arrived
  somewhere, which §1 rejects. `command_count` counts read-only commands, so a
  budget punishes the inspection operational git is mostly made of. **The
  vocabulary is twenty.** `test_registry.py`'s `VOCABULARY_SIZE` fired as a
  tripwire in the direction nobody plans for — removal — which is what it is for.

  `RepoQuery.reflog` and `ReflogEntry` went with them, and that part has a real
  cost recorded rather than glossed: the conformance suite loaded the fake's
  reflog positions *through* that method, so `HEAD@{0}`, `HEAD@{1}` and
  `HEAD@{3}` moved from its derived-and-therefore-tested list to its
  loaded-and-therefore-trivial one. Both sides are still tested individually; the
  cross-check between them is gone. Keeping a port method whose only consumer is
  the suite that proves it would have been worse — agreement with git about a
  method nothing calls is worth nothing.

**The oracle earned its keep eight times, which is the number worth keeping.**
Five counter-example failure sets were predicted wrong and corrected by
`test_scenarios.py`'s exactly-these-checks rule; three expected values in katas
were wrong arithmetic, caught by `test_katas.py` grading the reference. Two of
the three were in `house-robber`, where an "adjacent is illegal" example reached
a test, a prompt *and* the notes before anything ran, so the fix changed all
three. The practice that followed is now the rule for this kind of content:
**compute every expected value, do not reason about it.** The counter-example
corrections were all one shape — collateral from a check reading `HEAD~1` or a
remote-tracking ref — and the declaring-exactly rule caught every one on first
contact.

**Two authoring constraints nobody had written down.**

- **`SHELL_METACHARACTERS` are rejected inside quotes too.** `|<>&;` anywhere in
  a `.cmds` line is refused, so any file content a solution *writes* cannot
  contain them. It shaped two fixtures and broke one on first run:
  `resolve-a-conflict-during-a-rebase` resolved to `attempt < MAX_ATTEMPTS` and
  now reads `attempt in range(MAX_ATTEMPTS)`. This is the first thing to know
  before authoring a scenario whose answer edits a file.
- **A fixture must leave a clean worktree** (`test_its_fixture_leaves_a_clean_worktree`),
  so no scenario can *start* mid-conflict or with uncommitted work. The conflict
  track is authored around it — the solver runs the merge — and "recover
  uncommitted changes" is simply not expressible, which is honest, because git
  cannot do it either.

Two smaller ones: a fixture's own `git push` updates its remote-tracking refs as
a side effect, so "you have not fetched since yesterday" has to be restored
deliberately with `git update-ref` — two fixtures do, and without it the
stale-cache lesson in `pull-without-a-merge-bubble` was prose describing a state
the fixture did not have. And `git rebase --continue` needs an editor, which the
sandbox pins to `false`; `git commit --no-edit` first works, keeps the original
message, and is a real technique rather than a workaround, verified against a
live rebase before the exercise was written.

**The curriculum question was answered, and the revisit found the premise was
false.** §15 question 4 said "start hand-ordered; revisit once there are 50
exercises". Nothing was ever hand-ordered: `list_exercises()` returned
`sorted(ExerciseId)`, so the library was ordered by spelling —
`katas/edit-distance`, the hardest kata in it, appeared fifth, before
`climbing-stairs`. Invisible at three exercises; the first thing a solver sees at
fifty-four. `content/curriculum.yaml` now declares nine tracks in order and
`validate_library` requires it to name every exercise exactly once
([ADR 0014](adr/0014-a-hand-ordered-curriculum-manifest.md)). **No caller
changed** — the browse page and the unscheduled half of the review queue both ask
the library for the library's order, and `review_queue.py` had explicitly declined
to invent a local one on the grounds that "inventing half an answer to it here
would make the real one harder to add". It was right, and the payment arrived one
phase later. The tracks are a manifest rather than directories because they have
to be: an `ExerciseId` is exactly `<track>/<slug>` (§4.1), so the filesystem can
express two tracks and the phase has nine.

**ADR 0009 waited eleven phases and was worth waiting for.** Its number was
reserved in §12 before Phase 0 shipped, and it is about what `content/` contains,
so it could not honestly be written until there was content. The decision — every
prompt, hint, note, test and reference solution written here, nothing borrowed —
has a consequence that only shows up after authoring thirty katas: **writing the
prompt is what finds the discriminating test.** The tree a per-node BST check
accepts, the flood fill that loops forever on a no-op, the `abba` that breaks an
unguarded sliding window, `cars` with `["car", "ca", "rs"]` — none came from
reading a problem statement. They came from writing one and asking what a wrong
answer would look like, which is the step a copied statement skips. Every number
reserved in §12 is now written.

**The content suite is the slowest thing in the project, and the cost is worth
stating.** 936 cases over the real library: two pytest subprocesses per kata,
and per git scenario a provisioned workspace and a bash fixture per graded replay
— one for the reference and one for each of its counter-examples. Nine minutes on
its own. The per-exercise filter (`-k <slug>`) is what made authoring possible at
all: each exercise was graded in about four seconds while being written, and the
whole suite only before each commit.

**The cheap tier cannot see a content commit at all, and this is the phase that
proved it.** §11's per-commit loop derives its test paths from the test
*directories a commit touches*, and a commit that adds only `content/` touches
none — so it runs lint, format and `mypy` over data those three tools do not
read, and then nothing. Which means the loop reported green on six content
commits while an e2e test was failing.

What it was: the dashboard offers the **top six rows** of the queue, and
`tests/e2e/test_schedule_a_review.py` asks for Two Sum there, solves it, and
asserts it is no longer offered. At three exercises Two Sum was always visible.
At fifty-four it was the fifty-second row alphabetically, and then the *seventh*
under the first draft of the curriculum — a first track of six git exercises
pushed every kata off the first screen. So the manifest was wrong in a way the
test was right about: interleaving at track granularity does not interleave the
first thing anybody sees. The fix is a four-long `start-here` track of two git
exercises and two katas, which is a better curriculum as well as a passing test.

Two things worth taking from it. The cheap tier's caveat list needs a sixth
entry — *a commit that only adds content runs no tests at all, so the pre-push
run is the only tier that covers it*, now in §11 and in CLAUDE.md — and the e2e
suite is the one that notices, because it is the only suite that reads the real
library through the real web app. Both other content-shaped defects this phase
(the metacharacter rejection, the fixture's clean-worktree rule) were caught by
`-m content` within seconds; this one needed the whole thing.

The durable fix is a content test rather than a careful manifest:
`test_the_first_screen_of_the_curriculum_offers_both_kinds` asserts that the
top `QUEUE_LIMIT` entries of the curriculum include at least one of each kind,
which is the property the e2e depends on, checked in milliseconds where the
author will see it.

**Six of this phase's commits do not pass that e2e test, and that is what
retired §11's per-commit greenness rule** (see the entry below). It failed from
content commit 1 — which took the library from 3 exercises to 11, pushing Two Sum
out of the dashboard's top six rows — and nothing was green on it again until the
manifest's `start-here` track landed in commit 11. The rule was not broken by
skipping the tier; the tier was run on every commit and *cannot see a content
commit at all*, which is the finding above.

The phase closed at **3,095 tests** — 747 more than Phase 10, and 862 of those
are the content suite growing from 74 cases to 936 as it walked a library that
went from 3 exercises to 54 — with `domain/` and `application/` at **100%**
statement and branch coverage against the 90% gate.
The covered surface **shrank**: 1,977 statements and 384 branches, against Phase
10's 1,996 and 386. That is the arithmetic of the phase in one line. It added 51
exercises and four lines of domain code (`reference_failing_commands` and its
bound, `alias_name`), and deleted two assertions, a port method and a value
object — so the thing the coverage gate polices got *smaller* while the library
it exists to grade got eighteen times bigger. `practice validate` reports 54 exercises valid and
`practice fixtures --check` matches all 24 fixtures against `fixtures.lock`.

The whole suite now takes **17 minutes**, of which the content suite is nine.
That is the real cost of this phase and it is charged to the right place: the
pre-push tier. Nothing else got slower, because nothing else grew.

**2026-10-03 — the per-commit greenness rule is removed, and the suite is
17m21s → 3m42s.** Two changes, prompted by the same complaint: Phase 11 spent
over two hours of wall clock waiting for tests, which is not a price this
project can pay again.

**The rule went first, because it was the thing generating the waiting.** §11
had said *every commit in a phase must be green on its own*, enforced by a loop
that checked out each commit and ran its test directories against it — plus a
second loop to attribute a failure when the first went red. The reasoning for
removing it is in §11 and worth summarising: it priced bisectability above what
bisectability is worth here, it could not see a content commit at all (so it was
already not holding for seven of Phase 11's thirteen commits), and the failure
it guards against is cheap to find and cheap to fix. What survives is the weaker
claim that **a commit list is a dependency order** — checked by `mypy` over the
working tree, which names a missing import for free. The two tiers are now one
fast tier on the working tree and one gate before a push, with no `git checkout`
anywhere.

**Then the suite was measured rather than guessed about, and the result was not
where anyone was looking.** `pytest --durations=40` over the whole run:

```
49.13s  tests/integration/test_cli_sandbox.py::test_write_then_check_agree
48.92s  tests/integration/test_cli_sandbox.py::test_write_is_reproducible
37.78s  tests/integration/test_cli_sandbox.py::test_it_names_every_exercise_it_checked
31.21s  tests/integration/test_cli_sandbox.py::test_the_shipped_fixtures_match_the_lock_file
28.90s  tests/integration/test_cli_sandbox.py::test_a_changed_fixture_fails_the_check
26.51s  tests/content/test_fixtures.py::test_the_lock_file_matches_the_library
...
```

**Nine tests in one file cost 288 of the 1,053 seconds — 27% of the suite.**
Not the content suite, which is where the suspicion was. `practice fixtures`
runs every git scenario's fixture, and the tests that needed a library they
could *break* copied the whole shipped one — so the library was fingerprinted
nine times over. At two scenarios that cost a couple of seconds each and nobody
noticed; at twenty-four it is five minutes. **A cost that was invisible at the
size the test was written for and linear in content the tests do not care
about.** That is the shape to look for next time.

Four changes, all of them removing duplicated work rather than hiding it:

- **`test_cli_sandbox` breaks a two-exercise subset**, built once per session
  and copied per test, instead of copying all fifty-four. They are still real
  exercises — that was the point of copying rather than hand-building — and what
  is dropped is twenty-two repetitions of the same evidence. The two tests that
  must see the shipped library share one invocation. **288s → 41s.**
- **`test_the_lock_file_matches_the_library` became
  `test_its_fixture_matches_the_lock_file`.** This file provisions every
  scenario anyway, and a `FixtureFingerprint` is just the workspace's aliases
  and refs — so the comparison costs nothing where `fingerprint_library` over
  the library cost twenty-four more fixture runs. Same claim, per-exercise
  failure message, **−27s**.
- **One pristine workspace per scenario** in `test_fixtures`, shared by the six
  tests that only read it. Six fixture runs to look at the same end state was
  five wasted. The two tests that *mutate* a repository still take their own,
  which is the invariant to keep: if a test changes the repository it does not
  belong on that fixture.
- **Reference and stub verdicts are memoised** in `test_scenarios` and
  `test_katas`, where two tests each read one verdict and were each paying for
  it. Memoised rather than `scope="module"` for a reason worth recording: the
  autouse `_own_database` fixture monkeypatches the database path *per test*, so
  a module-scoped `Services` would outlive the environment it was built under.
  Caching the resulting `Submission` has no such problem — it is data.

That took the suite from **17m21s to 10m10s** with the content suite falling from
527s to 298s, and 3,118 tests passing against 3,095 before (the per-scenario lock
check is twenty-four tests where the library-wide one was one). Every second of
that is work that was being done more than once.

**Then `pytest-xdist`, where the obvious setting turned out to be the wrong
one.** The suite is subprocess-bound — a bash fixture and a dozen `git`
invocations per scenario, a `pytest` per kata — so it ought to parallelise well,
and `-n auto --dist loadfile` on twelve cores first ran in **3m42s** with the
coverage gate. That number is real and it is not reproducible:

| workers | wall clock, with the gate | repeatable? |
|---|---|---|
| serial | 10m10s | yes |
| `-n 4` | **7m20s** | yes (twice) |
| `-n auto` (12) | 3m42s, then 7m36s, then 8m41s | **no** |

Twelve workers each starting their own processes oversubscribe a twelve-core
machine, and the times swing by more than a factor of two. **One of those runs
failed**, which is the part worth having: two tests in
`tests/integration/kata/test_pytest_runner.py` reported *no test failures* for a
deliberately wrong solution. Not a parsing bug — the inner `pytest` had been
killed by its ten-second wall-clock limit, no report was written, and
`_read_report` correctly returned `None`. A suite that grades against real time
limits cannot be run on a saturated machine.

Half of that is a genuine fragility and is now fixed: every test on that file's
`spec` fixture is about what the runner *reports* — parsed records, docstring
labels, ANSI escapes, which config it obeyed — and none is about the limit, which
has its own `kata_spec_with_a_short_limit`. They inherited two-sum's real ten
seconds for no reason, so `spec` now lifts it to two minutes. A loaded CI runner
could have flaked those at any point in the last seven phases.

The other half is not a bug: `tests/content/test_katas.py` grades every kata
against its **real** declared limit, deliberately, because that is the limit a
solver is held to. So the suite stays wall-clock sensitive by design, and the
answer is to stop oversubscribing rather than to stop asserting. **`-n 4`**,
measured and repeatable, is what the documented command uses. CI uses `-n auto`
for the same reason this machine does not: a GitHub runner has two cores, so
`auto` is two workers there.

Deliberately **not** in `addopts`. Four workers to run one file is slower than
one, and the fast tier runs one file; the flags live on the documented pre-push
command and in CI, where the whole suite is what runs. `-n0` turns it off.

**What was not done, and why.** No test was deleted and no coverage was given
up: the suite still grades every reference solution, every counter-example
against exactly its declared checks, every stub, and every fixture against the
lock. The 17 minutes were not the price of that evidence — they were the price
of collecting some of it nine times. Worth saying plainly, because "the suite is
too slow" invites deleting tests, and deleting tests was never the cheapest
thing available here.

**Where the remaining time is, if this comes up again.** `--dist loadgroup` with
a group per `(module, exercise)` would balance far better than `loadfile`, which
currently leaves the longest file — `test_scenarios` at 138s — setting the floor
for the whole run. That is the next lever and it needs a
`pytest_collection_modifyitems` hook to assign the groups, which is why it was
not taken today.


**2026-10-03 — Phase 12 complete, and v1.0.0.** Four commits, exactly the four
§11 sketched, which had not happened in any previous phase. Three deviations,
and the interesting one is not the demo.

**`practice up` is a second command, not a change to `serve`, and a test is why.**
The plan says "`practice` launcher: first-run setup, migrations, browser open",
and the obvious reading is that `serve` grows those. It cannot:
`test_building_the_app_reads_no_database` pins `serve` to creating no database
on startup, and that property is what makes `serve` the command CI and the whole
web suite can boot. A `serve` that migrated eagerly would have to give it up, or
grow a `--setup/--no-setup` flag — which is two commands again, spelled worse.
So the setup went into `up`, and the loopback guard and the `uvicorn.run` call
were extracted into `_bound` and `_listen` so §8.3's first guard still has one
implementation and one test covering both ([ADR 0017](adr/0017-a-front-door-separate-from-the-server.md)).

**The design question underneath it was whether to stop at the first failure.**
A chain is the tempting shape and it is wrong for a tool somebody has just
cloned: a machine with no git plausibly also has no writable data directory, and
two runs to learn two facts is one too many. So every step runs and `FirstRun`
collects them, every step catches its own exceptions rather than letting one
propagate and take the other three with it, and
`test_it_reports_every_blocker_rather_than_the_first` holds it. The price is a
side effect on a run that then refuses — the workspace directory and the
database file are created even when git is missing — which is bounded by
`test_prepare_creates_nothing_it_was_not_asked_to` and is cheaper than a report
that cannot tell you whether the next thing is also broken.

**The demo is generated, not recorded.** A GIF needs a recording tool and an
encoder, which means re-resolving a lock file this project resolves once on
purpose; and a GIF of a terminal is a picture of text, so a reviewer who wants
to check that the verdict in the README is the verdict the tool prints has
nothing to check against. `docs/demo/session.txt` is the captured output of a
real `practice solve` and `docs/demo/render.py` draws it
([ADR 0016](adr/0016-a-generated-demo-not-a-recorded-one.md)). Two findings
while writing the renderer, both from running it:

- **The obvious animation encoding does not loop.** One shared keyframes plus a
  per-line `animation-delay` seems right and is not: with `infinite`, each line
  repeats on *its own* cycle starting from its delay, so the screen never clears
  at once — every line flickers off at a different moment. One keyframes block
  per line, with the reveal point baked in as a percentage of one shared
  duration, is what makes them start and end together.
- **The static fallback is the reason this is safe.** Every line is authored
  with `opacity="1"` and hidden by the stylesheet, so a renderer that strips CSS
  shows the whole transcript rather than an empty box. That is the opposite of
  the usual failure mode for an animated SVG, and it is why depending on CSS
  inside an image is an acceptable risk here.

**The third deviation is an ADR for a decision this plan already held.**
[ADR 0015](adr/0015-verify-on-the-working-tree-not-every-commit.md) records the
removal of the per-commit greenness rule, which was Phase 11's decision and
lived only in §11 and §16. The ADR index says a retrofitted record keeps the
justification and loses the alternatives, so the file says up front that it is
an exception and why it is not a reconstruction: the reasoning and the
measurements were written at the time, and what the ADR adds is the alternatives
section the plan never had.

**One defect, and the fast tier could not have found it.** The first line a
stranger reads — `54 exercises (24 git scenarios, 30 katas) in …` — had an em
dash in it, and `chcp 437` is still the default on a fresh Windows console, so
it arrived as a replacement character. Found by running the command, not by any
test: every assertion on that line matches a substring that does not contain the
dash, and would have gone on passing. The report is ASCII now, with a comment
saying why. **The general shape:** a test suite asserts on the string the
program *produced*, and the console is a second encoder between that string and
the reader.

**A fourth small thing the plan did not list, and it is the same genre as the
other two.** §11's commit list for this phase ends at "tag `v1.0.0`", and a tool
that claims a version with no way to ask it for one is the third instance of the
omission §16 already records for `practice start` and `practice serve`: the
thing a *user* types keeps being the thing left out. `practice --version` reads
the installed package metadata rather than a constant, so `pyproject.toml` stays
the only place a version number is written — and the test asserts against that
metadata rather than against `1.0.0`, which would pass on the next release and
be wrong.

**Final numbers.** 3,138 passing and one skipped, in 7m40s on four workers --
twenty seconds slower than Phase 11 left it, which is this phase's seventeen
integration tests and nothing else. 100% statement and branch coverage over
`domain/` and `application/` against the 90% gate, 54 exercises, 24 fixtures
pinned on both platforms, 17 ADRs. Seventeen use cases, 13 ports, 20 assertions.
`uv run practice up` is the whole of getting started.

**What is still wrong is written down rather than implied** —
[the postmortem](postmortem.md) names five things, of which the two worth
repeating here are that the longest *file* sets the floor for the parallel suite
(`--dist loadgroup` is the known lever) and that an advisory check prints a label
describing the passing state even when it fails, so "You did not force-update a
shared branch" appears directly above the evidence that you did. It reads wrongly
in exactly the output this project puts in its README.

---

**2026-10-04 — Phase 13, first item: FSRS, and a prediction graded.** Five
commits, exactly the five sketched, one session. Phase 13 is a menu of eight
stretch ideas to be picked by appetite, and the appetite had a tiebreaker:
**every other row in the table would have produced a feature, and this one
produced a graded prediction.** ADR 0008 deferred FSRS in Phase 9 and wrote down
in advance what the swap would cost, which makes it the only item in the menu
whose outcome could be *wrong*. It also cleared the last port satisfying §13's
two-implementation rule on an IOU: `Scheduler` had one real implementation and a
double that does no arithmetic.

**ADR 0008's prediction held, and the part it missed is the interesting part.**
It said FSRS would be "a second class satisfying the same protocol and one line
in `composition.py`", and the line was exactly where it said: `Sm2Scheduler()`
became `build_scheduler()`. It said an honest migration "would add columns rather
than reuse them", and `0002_fsrs_memory_state.sql` adds two nullable ones.
Twelve files under `src/`, and **not one of them a use case, a grader or a
route** — `application/`, `domain/checks/` and the sandbox, git, kata and
content adapters are untouched. The two that are neither scheduler, root nor
interface are the SQLite mapper and the review repository, each gaining the two
column names, which is the honest asterisk on "one line": a new column has to be
named where rows are built, and the ADR predicted that half too.
**What it did not foresee is that one line is not shipping.** A second
implementation nobody can select is written rather than shipped, so the real bill
was one line *plus* a registry in `composition.py`, a question in `config.py`, a
fifth preflight step, and a branch in one template — four additions, all four of
them in the interface or at the root, which is the shape §13 asked for and not
the shape the ADR promised. The correction is in ADR 0018 rather than left as a
prediction that was nearly right.

**Finding one: three of §9.7's four properties belong to the port, and one
belongs to SM-2.** This is the finding the whole phase was worth. §9.7 names four
properties of "the scheduler" and Phase 9 held them in `test_sm2.py`, because
with one implementation there was nowhere else to put them and no way to tell
which kind of claim each one was. The ease floor, monotonicity under consecutive
`GOOD`, and `due_on` always falling after the review are properties of *a*
scheduler, and they now live in
`tests/unit/domain/scheduling/test_scheduler_conformance.py`, parametrized over
both. *"`AGAIN` always resets to one day or less"* is **SM-2's policy**: FSRS
schedules a lapse from its own post-lapse stability, which on a card established
for a year is weeks, and bending it to a day would have been bending the second
implementation into the first's shape to protect a sentence in this document.
What replaces it as a shared property is the weaker and still useful *a lapse
never lengthens an established interval*.

The general lesson is worth stating because it will recur: **a property believed
universal and actually local is a liability**, and the only way to find one is a
second implementation. The conformance suite is where any third scheduler gets
held, and `test_every_real_scheduler_is_covered_here` exists because a scheduler
added and not parametrized in is one nothing holds to the contract and no other
test would notice.

**Finding two: §9.7's interval clamp is a property of whole-day intervals, not
of SM-2.** §9.7 introduces `max(previous + 1, round(interval * ease))` as the fix
for a stall at the ease floor — `round(1 * 1.3) == 1` — and reads like a quirk of
one algorithm's arithmetic. FSRS stalls too, from a cause with nothing in common:
its stability grows by `1 + k * (exp(w10 * (1 - R)) - 1)`, which is **exactly 1
when `R == 1`**, and retrievability is 1 whenever no days have passed. Grade a
card twice in one day and FSRS hands back the stability it was given. Two
unrelated causes, one fix, and §9.7's instruction to "write the test first and
watch it catch this" was vindicated a second time by a test written for a
different implementation.

**Finding three: the one defect the test suite could not see was in a template
again.** The schedule panel printed `Ease 2.50` unconditionally. Correct under
SM-2; under FSRS a constant that never moves and means nothing — and *present,
and correctly formatted*, so no fragment assertion in `tests/web/` was ever going
to fail on it. Found by setting `PRACTICE_SCHEDULER=fsrs` and reading the page,
which is now the third time this project has found a real defect that way: Phase
9's four accent-on-accent buttons with no words on them, Phase 12's em dash
arriving as a replacement character on a fresh Windows console, and this. **The
pattern is stable enough to state as a rule: a surface whose correctness depends
on which implementation is wired behind it cannot be covered by asserting on its
output alone.** The fix pushes the claim down to where a test can hold it —
`ReviewCard.has_memory_state` decides which numbers are meaningful, the template
decides what to call them, and `tests/web/test_review.py` now has both branches.

**Two deviations from FSRS-4.5 as published, both deliberate.** A lapse is
clamped so it never lengthens an established interval: the published post-lapse
term can exceed the input stability where stability is small, and the property is
worth more than fidelity to a formula whose seventeen parameters this project
cannot fit. And there is **no maximum interval**, which FSRS implementations
normally have, because `min(ceiling, ...)` and `max(previous + 1, ...)` cannot
both hold — a ceiling would break the monotonicity property the moment a card
reached it, to protect against a card nobody will own.

**The thing that made a mid-history switch survivable was an identity, not a
migration.** At 90% retention an FSRS interval *is* its stability, exactly,
because `0.9 ** -2 - 1 == 0.19 / 0.81 == 19 / 81` is the forgetting curve's own
factor and the two cancel by construction. So a card SM-2 left at fifteen days is
read as a card with a stability of fifteen and **adopted** rather than reset. The
alternative — treat an unknown memory state as a new card — would have discarded
a month of real review history on the day the choice was changed, invisibly. One
ulp out in float64, so the test asserts it with `isclose`; exact in arithmetic,
which is what makes it a conversion rather than a guess.

**Three test-suite repairs, two of which had been passing for the wrong reason.**
A migration-count assertion compared the applied versions to a literal `[1]`, and
a second test fabricated "a database written by a newer `practice`" as version
**2** — which this `practice` now ships, so it had stopped testing a refusal and
started constructing an entirely ordinary database. Both now derive from
`load_migrations()`. **A literal that names a version from the future is
guaranteed to stop being one**, which is a small enough lesson to have missed and
a sharp enough one to write down. The third: `conftest.py` now clears
`PRACTICE_SCHEDULER`, for the reason it already redirects the database — a
developer with `fsrs` exported would otherwise run a different wiring than CI,
and only on their machine.

**What was not taken, and why.** The Docker sandbox adapter is the one item that
cannot be verified on this machine or kept inside the offline claim (§8.2), so it
stays open as a design sketch rather than a half-tested adapter. Shell drills, SQL
drills and concept recall each mean a new *exercise kind* — a grader, a schema
entry and authored content — which is Phase 11's shape and not a stretch item's.
Interview mode is the cheapest remaining item and the most self-contained, and it
is the one to take next if the appetite returns.

**Final numbers.** 3,219 passing and one skipped, in 8m11s on four workers —
81 more tests and 31 seconds more than Phase 12 left it. 100% statement and
branch coverage over `domain/` and `application/` against the 90% gate, and the
covered surface **grew** for the first time since Phase 10: 2,077 statements and
402 branches, against Phase 11's 1,977 and 384. That is this phase in one line
and it is the mirror image of Phase 11's, which shrank the gated surface while
multiplying the library — a hundred statements of new arithmetic, all of it
inside the gate, because a scheduler is the kind of thing that can be quietly
wrong and `domain/scheduling/` is where this project puts those. 54 exercises
unchanged, 24 fixtures pinned on both platforms, **18 ADRs**, 2 schema
migrations. Two real `Scheduler` implementations and a double, which is the
first time §13's two-implementation rule is met by this port without counting
the double.

**One cost worth recording against this phase specifically.** FSRS is shipped and
not defaulted, and the reason is the one ADR 0008 already gave: its advantage
comes from parameters fitted to a log of real reviews, `sqlite/reviews.py`
replaces a card on every review and keeps none, and **FSRS on unfitted defaults
is FSRS without the thing that makes it better than SM-2**. So this phase bought
a proof about the architecture and a finding about the properties, and bought the
user almost nothing. That is a fair trade for a stretch item and would not be one
for a planned phase. The review log is the thing that would change it, and it is
a phase rather than an afternoon: a schema change, a repository method, a backfill
with nothing to backfill from, and a fitting procedure.


**2026-10-04 — Phase 14: the third exercise kind, and a prediction half graded.**
Five commits, two sessions. SQL drills, taken from Phase 13's menu for the same
reason FSRS was taken first — it was the item with a *prediction* attached, and
the only other place in the project carrying one. `domain/exercise.py` has
claimed since Phase 1 that a third kind means "adding a spec and a registry
entry instead of re-cutting a class hierarchy". [ADR 0019](adr/0019-sql-drills-as-a-third-exercise-kind.md)
is the grade.

**The inheritance half held exactly, and that is the less interesting half.**
`SqlDrillSpec` is a dataclass beside the other two; nothing was subclassed, no
class was re-cut, `build_services` did not change at all, and `build_graders`
gained three lines of which two are a comment. No port was widened. Nothing
under `domain/checks/`, `adapters/git/`, `adapters/kata/` or
`application/use_cases/` changed in substance.

**The "and a registry entry" half did not, and the reason generalises.** Two
kinds is the number at which a discriminated union and an inheritance hierarchy
are indistinguishable: every `isinstance` is a boolean and every `else` is the
other case. Five call sites asked whether an exercise was a kata and *meant*
whether it had a file to edit — the workbench editor seed, the solution-file
handoff, `practice solve`'s next-step line, the fallback source it reads without
`--source`, and the template branch choosing a console over a CodeMirror pane.
None of them was wrong until a third file-based kind made the two questions
different. **The lesson is not "the union was the wrong shape"** — it was the
right shape, and the prediction was about the shape. It is that *a prediction
about the cost of a third case cannot be made from two cases*, because the thing
that costs is the conflation you cannot see yet. `editable_source` names the
question once and is total over the union, so a fourth kind pays none of it
again.

**Six findings, in the order they turned up.**

**`_PENDING` was unreachable by construction, so it is deleted.** The mapping
was kept empty since Phase 5 for a kind that exists before its grader does, and
`test_every_exercise_kind_has_a_grader` — added in that same phase — forbids
exactly that state. Phase 14 is the first time anything tried to use the
mechanism and found the suite already rules it out. §13's rule applied rather
than quoted, the same way Phase 11 deleted `reflog_contains` and
`command_count`. The consequence is structural: the commit list is five rather
than the seven sketched, because the kind, its schema, its grader and its
interface **had to land together**. Worth noting as a tension rather than a bug —
two mechanisms disagreed about whether a kind may exist without a grader, and the
stronger one was right.

**The old `if scenario ... else kata` was asserting that not-a-scenario means a
kata.** Widening the spec union turned `provisioner.provision` into the single
`mypy` error this phase produced, and it is the architecture test working in the
form that costs nothing to run: a two-branch dispatch over a two-member union is
indistinguishable from an exhaustive one until the union grows.

**The first-run library line counted by subtraction.** `scenarios =
len(exercises) - katas` in `launcher.py` would have reported eight SQL drills as
eight more git scenarios, in the first line a stranger reads. Same defect class
as the five `isinstance` sites, in the one place a type checker cannot see it:
the arithmetic stays valid, and only the *claim* stops being true. The general
form is worth keeping — **a count derived by subtracting one category from the
total is a count that silently absorbs a third category.**

**§15 Q3's prediction was nearly right, and the gap fails silently.**
`vendor.py` said a second language costs "a second line here and nothing else".
The second line is right, and `verify`, the offline grep, the asset route and
the hash test are all untouched. But `workbench.html` had
`codemirror-python.min.js` written into its script tag, so a drill would have
loaded a Python tokenizer and then asked CodeMirror for a `sql` mode it had not
loaded — degrading to a plain textarea with no error anywhere. **No existing
assertion could have caught it**, because the mode *name* was already coming from
the spec and was already tested. `vendor.mode_file` makes the mode-to-file map a
fact about the manifest rather than a path a template guesses at, and
`test_a_drill_loads_the_sql_mode_and_not_the_python_one` is the claim.

**`ParamValue` had no `float`.** Nothing in the git vocabulary has ever needed
one — a commit count is an integer, a ref is a string, `include_untracked` is a
flag. Four of the eight drills hold a money column, so `[[alice, 77.5]]` was
rejected by the schema with roughly twenty lines of Pydantic union errors, not
one of which said "no float here". Widening it loosens nothing, because
narrowness was never enforced by the type: it is enforced by the accessors, and
`Params.integer` still refuses a float. **The error message is the part worth
recording as unfixed** — Pydantic renders a failed recursive union by listing
every arm at every depth, and the project already accepts the same noise from
the `kind` discriminator. A better message would mean hand-rolling the
validator, which is a worse trade than a noisy one.

**Three content bugs, every one found by running the content rather than reading
it.** Which is the argument for `-m content` existing, restated:

- **A `LIMIT` that was vacuous on its own data.** Only three of four customers
  have non-cancelled orders, so `LIMIT 3` cut nothing: the counter-example
  written to demonstrate a forgotten `LIMIT` returned the right rows in the
  right order and failed nothing, and the `exactly-three` check could never have
  failed either. §5.4's vacuous-check failure, in content rather than in a spec,
  and caught by `test_a_counter_example_fails_the_check_it_declares` — which is
  precisely the assertion §5.4 argues for over "fails at least one check".
- **A counter-example that returned the reference's exact rows.** `GROUP BY city`
  and `GROUP BY COALESCE(city, 'unknown')` partition this data identically,
  because SQLite groups NULLs together; the mechanism the notes described was not
  the mechanism at work. The honest behaviour is now a footnote and the
  counter-example is `COUNT(city)`, which genuinely reports the unknown group as
  zero.
- **A query plan that scans the other table.** The exercise was right and the
  notes explaining it were wrong: with no index on `customers.name`, SQLite walks
  every *order* and looks each customer up by rowid, so the index on
  `orders(customer_id)` is not used at all. Both plans are quoted in the notes
  now, because which table gets scanned is the lesson and it is not the one most
  people guess.

**One architecture rule changed, and it is a clarification.**
`test_only_the_persistence_adapter_speaks_sqlite` becomes
`test_only_the_two_named_packages_speak_sqlite`. The original argument was about
*storage* — one schema, one set of migrations, one transaction boundary, behind
the repository ports — and with one database in the project, "storage" and
"imports `sqlite3`" were the same string. `adapters/sql/` keeps no schema, no
migrations and no file. The cost of admitting it is that the rule is a list with
a reason per entry, so two tests exist to stop the list rotting: every named
package must actually import `sqlite3`, and the drill engine must not reach the
application's database.

**One requirement the other two kinds got for free: idempotent re-grading.**
ADR 0013 grades on every Ctrl+S, so an answer runs tens of times — and `INSERT
INTO orders ...` against a persistent database gives a different verdict the
second time, while `UPDATE totals SET total = total * 2` gives a different one
every time. pytest against a file is naturally idempotent and a git fixture
rebuilds its repository, so nothing in the project had had to think about it. An
in-memory database seeded per pass is the fix, and it pays for itself three
times: nothing to confine, nothing to clean up on Windows, and `seed.sql` stays
readable on disk — which matters, because the solver is *meant* to read the
schema.

**The policy is SQLite's, not a regular expression.** The one thing worth
stopping is `ATTACH DATABASE`, and the spellings that defeat a pattern were
written out before choosing: `ATTACH/**/DATABASE`, `attach\n  database`, mixed
case — and a pattern strict enough for those refuses `SELECT 'ATTACH DATABASE'
AS note`, which is a correct answer. `set_authorizer` runs during statement
preparation and cannot be spelled around. That is ADR 0003's argument about
*grading* applied to *policy*, and it is the second time this project has
reached for a mechanism instead of a pattern and been glad of it.

**Final numbers.** **3,593 passing and one skipped, in 3m45s on four workers** — 374 more tests
than Phase 13 left it. **100% statement and branch coverage** over `domain/` and
`application/` against the 90% gate, and the covered surface grew again: 2,372
statements and 480 branches, against Phase 13's 2,077 and 402. Nearly three
hundred statements of new domain code, all of it inside the gate, because ten
assertion functions and a comparison policy are exactly the kind of thing that
can be quietly wrong.

Four of those branches had to be chased deliberately.
`domain/drills/evaluation.py` shipped at 91% on the first full run — a blob, a
boolean, and two malformed-`rows:` shapes that none of the eight drills reaches.
`tests/unit/domain/drills/test_evaluation.py` exists for them, and the gate
naming them is the gate doing its job: *no current content reaches it* is not
the same claim as *it is right*.

**62 exercises** — 24 git scenarios, 30 katas, 8 SQL drills — with 52 scenario
counter-examples and 16 drill counter-examples held to failing **exactly** the
checks they declare. 24 fixtures pinned on both platforms, **19 ADRs**, 2 schema
migrations. 17 use cases, **14 ports**, **30 assertions** across two disjoint
vocabularies. `git diff --stat v1.0.0..HEAD -- src/` is 34 files.

**One number I cannot account for and am recording rather than explaining.**
Phase 13 measured the full suite at 8m11s on four workers with a *smaller* test
count; two runs today, at the larger count, came in at 3m43s and 3m45s. The
times are repeatable, so the measurement is sound; what is not sound is any
story about why. The drill suite is the fastest content in the project — 113
tests in 2.6 seconds, against two pytest subprocesses per kata — but that
accounts for seconds, not four minutes. The honest reading is that §11's own
warning about `-n auto` applies to four workers as well: **wall clock on this
suite is dominated by subprocess scheduling and therefore by what else the
machine is doing**, and a single figure recorded in a revision log is weaker
evidence than it looks. Re-measure before believing either number.

**What this bought, and what it did not.** Unlike Phase 13, this one bought the
user something: eight exercises in a third discipline, and `query_plan_matches`
carries the most transferable idea in the track — two answers returning
identical rows can differ by any factor in work done, and SQLite will tell you
which is which. What it did not buy is any change to the engine's shape, which
was the point. The remaining Phase 13 items are unchanged except that **shell
drills and concept recall are now cheaper than they look**: the second exercise
kind cost an abstraction that a third would not pay for again, and
`editable_source` plus two disjoint check registries is the pattern a fourth
kind follows. Interview mode is still the cheapest item and the most
self-contained. Docker still cannot be verified offline on both platforms, and
still stays open as a sketch.

---

**2026-10-04 — Phase 15: interview mode, and a prediction that could not be
met.** Six commits, one session. The third item from Phase 13's menu, taken
because its prediction is written in the menu itself: the **Touches** column says
`application-layer policy` and Phase 14's log called it "the cheapest item and
the most self-contained". Two of its three clauses are exactly that. The third
is not implementable at all, and finding out *why* is worth more than the feature
([ADR 0020](adr/0020-interview-mode-withdraws-affordances-it-cannot-contain.md)).

**"No test peeking" was asking for containment, and §8.1 ruled containment out in
Phase 3.** A kata's `tests.py` is copied into the workspace because `pytest` must
run it from there (`adapters/kata/pytest_runner.py` runs
`pytest <spec.tests>` with the workspace as rootdir), the workspace is a
directory on the solver's own machine, and
`adapters/sandbox/command_policy.py` opens with the sentence that settles it:
*"Two jobs, and neither is security. The solver authored the content and owns the
machine."* The clause could not be delivered as written, and the two available
responses were to deliver something weaker under the same name or to rename it.
What shipped is `AttemptPolicy.reveals_workspace` — **every affordance the tool
provides for peeking is withdrawn, and the tool says that is what it did.** Two
of them: own-editor mode (refused in `load_solution_file`, so the browser and the
watch stream cannot disagree) and `practice start`'s next-step line, which stops
naming the path. A solver who goes looking for the cache directory will still
find the tests.

ADR 0020 spends its longest alternative on the stronger version — move the tests
out of `repo/` and point `pytest` at them — and rejects it for a specific reason
worth keeping: it needs `SandboxProvisioner.provision` to take the policy, which
is **a widened port, for one caller, to buy a boundary that still would not be
one**, because `pytest` has to be able to read the file either way. That is the
worst trade available in the phase, and the record says what evidence would
change it: somebody actually being tempted to read the tests.

**The two clauses that did fit cost almost nothing, and one of them cost
nothing.** Withholding hints needed no new code path anywhere: an empty `hints`
tuple makes `Attempt.reveal_next_hint`'s existing guard fire on the first
request, `remaining_hints` is already 0, and `workbench.html` already drew the
panel on `hint_count`. That is §4.3's claim about `AttemptPolicy` — *copy the
limits in and the aggregate enforces its own rules* — paying off as stated, and
the clearest single thing this phase can point at. What it did cost is one
sentence: the refusal said *"no hints left: this exercise has 0"*, which is false
when the exercise has four and the mode is keeping them.

**The clock needed no new grading rule, because the rule was already making the
comparison.** `suggest_grade` has read `elapsed > timedelta(minutes=
estimated_minutes)` since Phase 9, and an interview's deadline *is*
`estimated_minutes` — so a timed attempt was already graded from its end state
and a second comparison would have been two spellings of one number. Phase 15
went in expecting to add one and deleted the plan instead, which is §13's rule
about abstractions applied to a line of arithmetic.

**The Phase 13 ease-factor finding repeated, in a second place, and nothing could
have caught it.** `hints_used` is 0 for every interview attempt because none was
ever offered, and `review.html` printed *"passed clean, inside the estimate, no
hints"* — crediting the solver for restraint they had no opportunity to show.
Present, correctly formatted, meaningless: exactly what the schedule panel's
ease factor was under FSRS, and exactly as invisible to a fragment assertion.
`GradeSuggestion.hints_offered` is the denominator `hints_used` had always needed
and `declined_a_hint` is the question that sentence was always asking. It also
makes honest a case that was **always wrong and never visible**: an exercise
authored with no hints at all got the same undeserved credit, latent only because
the content suite requires every shipped exercise to carry some. Interview mode is
the first thing that produces a zero-hint attempt against an exercise that has
them.

**`practice solve` cannot be put into interview mode, and the flag is deliberately
absent.** Interview mode is about what happens *during* an attempt — a clock
running, a hint refused, a path withheld — and `solve` has no during: it opens an
attempt, grades the answer already written, and exits. A flag there would record
a set of rules nothing could have applied.
`test_solve_has_no_interview_flag` pins the absence, because an omission nobody
asserted is an omission somebody will fix.

**And one defect only running it could find.** Flooring the remaining minutes
greeted a fresh fifteen-minute interview with *"14 minutes left of 15"* — the
clock is read microseconds after `started_at`, and 14:59.9 floors to 14. It reads
as a bug and is not one. Fixed in three places and the leans are now opposite on
purpose: time left rounds **up** (a clock face does, and flooring would announce
"0 minutes left" to somebody with fifty seconds in hand), overrun rounds **down**
(two and a half minutes late is not three), and `practice start` prints the
*limit* rather than a countdown, because an attempt created a moment ago has its
whole limit left by definition. §11's "run the content, do not read it" gotcha
generalises: this was invisible on the page and obvious the moment
`practice start --interview` ran once.

**Two cleanups the phase forced rather than chose.** The dashboard and the browse
list each held their own copy of a two-line start form; adding the checkbox to
both would have been the first time those copies could disagree about what
starting an exercise means, so they became `partials/start-attempt.html`. And a
`noqa: TC003` in `domain/attempt.py` became genuinely unused once `deadline` and
`remaining` started constructing a `timedelta`, so the runtime import is now
load-bearing on its own rather than by argument.

**Migration 0003, and ADR 0008's asterisk holding for a third thing.** Two
columns, `NOT NULL DEFAULT 'practice'` and a nullable `deadline_seconds`. It
differs from 0002 in one way worth stating: 0002's columns are nullable because
NULL *means* something there (no FSRS has touched this card), while `mode` has no
such reading — every attempt already in the table ran under the only rules that
existed, so there is a correct value to backfill with. A nullable mode would have
invented a third state nothing can interpret. The pairing CHECK is enforced in
both directions, which is what a `bool` column could not have expressed, and the
prediction ADR 0008 made for a scheduler holds again: a new field on a stored
aggregate has to be named where rows are built. Two lines in the mapper, two in
the column tuple, and nothing else.

**Final numbers.** **3,656 passing and one skipped, in 3m52s on four workers** —
63 more tests than Phase 14 left it, which is the smallest increment of any
phase since Phase 0 and the right size for a phase that added no engine.
**100% statement and branch coverage** over `domain/` and `application/` against
the 90% gate, with the covered surface at 2,419 statements and 496 branches
against Phase 14's 2,372 and 480. Forty-seven statements and sixteen branches of
new domain code: a mode, a pairing guard, three clock accessors and a
denominator.

**What this bought, and what it did not.** It bought the user a second way to sit
all 62 exercises, which is the first stretch item to improve the whole library
rather than extend it. It bought the architecture its cleanest result yet —
no port widened, no grader touched, and the only adapter it reached is
`adapters/persistence/` for the two columns — and that result has an asterisk on
it, because the clause that would have reached the sandbox was dropped rather
than paid for. **The menu's `Touches` column is right
about the feature that was built and wrong about the feature it described**, and
the honest summary is that the cheap version of interview mode is
application-layer and the version in the menu is not. The remaining five items
are unchanged. Shell drills and concept recall are still cheaper than they look
for Phase 14's reason; Docker still cannot be verified offline on both platforms;
exportable content packs are now the cheapest item on the menu and the only one
that would give a port its second real implementation.

---

**2026-10-04 — Phase 16: content packs, and a port that was taking §13 on
credit.** Six commits, one session. The fourth item from Phase 13's menu and the
first the project nominated for itself: Phase 15's log closed by calling
exportable content packs "the cheapest item on the menu and the only one that
would give a port its second real implementation". Both halves of that held. The
**Touches** column's claim — *a content repository adapter* — held for the
adapter and was wrong about the feature, in the direction that was worth finding
out.

**`ContentRepository` is the catalogue, not the content, and nothing had said
so.** `SandboxProvisioner` is constructed with a `content_root: Path` and
resolves `content_root / exercise_id` itself, so a fixture, a stub, a `tests.py`
and a `seed.sql` reach a workspace by being copied from a directory and never
through the port. The library has two readers and only one of them is behind a
protocol. So a pack-backed `ContentRepository` serves a library that can be
browsed, filtered, counted, scheduled against and validated, and in which
nothing can be attempted — which is not a bug in the adapter but a fact about
where the port sits. ADR 0021 spends its longest alternative on the widened port
that would have fixed it and rejects it for a reason that only became clear while
writing it down: **the files have to be written to a directory either way.**
`pytest` runs a kata's tests from the workspace, `bash` executes a fixture from a
file, SQLite reads `seed.sql`. A port carrying bytes does not remove the
extraction; it moves it inside `provision` and makes it happen per attempt
instead of once per install. The finding is now a paragraph on the port rather
than a line in a record.

**The two indexes have to be derived, and this is the one thing the format could
not do naively.** `curriculum.yaml` and `fixtures.lock` are both per-exercise
indexes over a whole library. A pack of *part* of one that carried them verbatim
installs to a content root that fails **both** of the commands CI runs over
`content/` — `practice validate` because the manifest names exercises that are
not there, and `practice fixtures --check` because a lock entry has no exercise.
Deriving them is four lines and the interesting part is that the failure lands
in two different commands with two unrelated-looking messages. A pack with no
scenarios in it still carries a lock file, header and nothing else, because
`--check` refuses a root without one and an empty lock is exactly right about a
library with no fixtures.

**The determinism claim extends to the archive, and a zip is built to break it.**
A zip entry records a modification time and a unix mode, both properties of the
machine that wrote it, so the same library exported on two machines would
differ — and a pack that cannot be compared across platforms cannot carry the
Phase 3 claim it ships `fixtures.lock` to make. Fixed timestamp, fixed mode,
sorted entries. The one that matters most is the dullest: **bytes copied as
bytes.** A fixture read in text mode on Windows gains CRLF, and the history it
then builds is different *and valid-looking* — so the failure would not be a
missing file but twenty-four hash mismatches that read like a broken
environment. `test_an_installed_library_is_byte_identical_to_the_source`
compares all 355 exercise files directly, and the e2e scenario test grades the
reference against the pinned checks as the backstop.

**`__pycache__` was already in the content tree.** `content/katas/two-sum/`
holds one, because a kata's `tests.py` is importable and the content suite runs
it. A packer that copied whatever it found in an exercise directory would
therefore have produced a different pack depending on what had been run
recently — non-determinism arriving from outside the library, invisible in a
diff of it. Excluded by name, with the reason in the constant rather than in a
commit message.

**The export reads its own pack back before calling it good**, which was added
as belt and braces and turned out to be the only cheap check on the derivation.
Writing an archive is the easy half; a derived `curriculum.yaml` that the parser
which produced it would reject is a failure the writer cannot see in itself, and
opening the pack through the real `ContentRepository` costs milliseconds.

**And one thing that cost nothing, which is ADR 0017 paying off in a phase that
did not plan to use it.** An installed pack needs no new way to be reached:
`--content-root` is already on `solve`, `validate`, `fixtures`, `serve` and
`up`, so `practice pack --install` finishes by printing two commands that
already worked. The e2e test grades a kata and a git scenario out of an
installed root with nothing pointing at `content/`, and not one line of the
solve path was touched to allow it.

**One stale suppression, found by lint rather than by thought.** The CLI's
`from pathlib import Path` carried a `noqa: TC003` because Typer reads the
annotation at runtime; `pack` gave the module a runtime `Path(...)` call, the
rule stopped firing on its own, and `RUF100` then flagged the directive. The
reason it existed is kept as a comment, because the next person to remove that
call needs it.


**Final numbers, and the most interesting one is a number that did not move.**
**3,737 passing and one skipped, in 3m49s on four workers** — 81 more tests than
Phase 15 left it. **100% statement and branch coverage** over `domain/` and
`application/` against the 90% gate, with the covered surface at 2,419
statements and 496 branches — *exactly* Phase 15's figures, to the statement.
This is the first phase to ship a feature and add nothing at all inside the
gate, and that is the architecture reporting its own shape rather than a
coincidence: a pack format, a second repository and a CLI command are an
adapter, an adapter and an interface, and the only thing the phase put in
`domain/` is a docstring on `ContentRepository`. 62 exercises unchanged, 24
fixtures pinned on both platforms, **21 ADRs**, 3 schema migrations.

**What this bought, and what it did not.** It bought the library an exit: the
62 exercises are now a 360 KB file that somebody else can check and install, and
a subset of them is a library in its own right, which is what makes "here is my
SQL track" a sentence the tool can honour. It bought `ContentRepository` the
second real implementation it had been owed since Phase 2, and the honest
version of that is that writing one is how the port's actual scope was
discovered — it is the *catalogue*, and the thing that had been standing in for
the rest of it is a `Path` on the provisioner. What it did not buy is any way to
work from a pack without installing it, and ADR 0021 argues that is not a
missing feature.

The remaining four items are unchanged. Shell drills and concept recall are
still cheaper than they look for Phase 14's reason, and Phase 16 adds a small
cost to both: a fourth kind now has to be packable, which
`test_every_kind_in_the_library_survives_the_round_trip` is phrased to catch on
the day it is added. Docker still cannot be verified offline on both platforms
and still stays open as a sketch. The embedded terminal is now the only item
left whose **Touches** column has never been tested against anything, and on the
evidence of the last four phases that column is worth about as much as the
prediction it is attached to.

**2026-10-05 — Phase 17: the Blind 75 fill-in, and sixteen tests and claims
that were wrong about their own point.** 53 katas, taking the library from 62 exercises to 115.
The first phase since Phase 11 to be mostly content, and the first to produce an
ADR about *authoring* rather than about architecture.

**The scope was chosen by technique gap, not by list position.** The request was
"add the blind 150", which is not a list — Blind 75 and NeetCode 150 are the two,
and the gap analysis is what made the choice answerable. Of Blind 75, 22 were
already present. Of NeetCode 150, roughly 127 were missing, and the tags said
why that number is misleading: `arrays`, `dynamic-programming`, `trees` and
`graphs` were already covered eight to nine deep, while `binary-search`,
`stack`, `linked-lists` and `sliding-window` had **one kata each** and
backtracking, tries, union-find, bit manipulation and heap-design had **none**.
So the marginal exercise inside a covered family buys much less than the first
exercise in a family the library cannot teach at all, and the 53 were taken in
that order: linked lists, bit manipulation, grid index work and binary-search
variants first, because those were the families at zero or one.

**Sixteen adversarial tests and claims were wrong, and the six that mattered
were ones the content suite cannot see.** This is the phase's finding and it earned
[ADR 0022](adr/0022-counter-examples-are-run-against-the-bug-they-name.md).
`tests/content/test_katas.py` proves `solution.py` passes and `stub.py` fails,
and says so carefully in its own docstring. It caught all seven of the wrong
*expected values* immediately, which is the half it is good at. The six that
left the reference passing — tests that could not fail, or did not discriminate
— were invisible to it, and **three of those were found only by a code review
after the ADR was written.** The cheapest to describe: `find-a-word-in-a-grid`'s
counter-example for a permanent `visited` set in place of real backtracking was
a 3×3 ring of `A`s around a central `B`, which reads as obviously discriminating
and which the broken solution passes. Brute-forcing every 2×2 and 2×3 grid found
the real minimal case, a 2×2 `AA`/`AB` with the word `AAAB`.

**Two could not fail at all**, which is worse than being wrong. A
long-string palindrome test inserted a mismatching character at the *exact
centre* of a palindrome — which leaves it a palindrome. And an
`insert-an-interval` test asserted a hand-counted length of
`25_000 + 1 + 25_000`, which is precisely the off-by-one the test existed to
catch; it now compares against the oracle, on the rule that **an expected value
needing the same arithmetic as the code under test is not an expectation.**

**One was a claim rather than a value, and the correction is a better lesson than
the original.** `best-time-to-buy-and-sell`'s reference docstring asserted that
updating the running minimum before recording the profit permits a same-day
trade and is a bug. It is not: the illegal trade is worth exactly zero and the
accumulator already floors at zero, so both orderings are correct. Brute-forcing
every price list up to length seven found zero disagreements. The docstring now
makes the stronger point — *an impossible case that cannot win does not need
excluding* — which is a real habit, where the original was a memorised rule that
happened to be false.

**The exhaustive sweeps are the phase's main cost and its main defence.**
`find-words-in-a-grid` against the single-word search over 380,100 (grid,
word-list) pairs; `best-path-sum-in-a-tree` against a path enumerator over
140,680 trees; `alien-alphabet-order` against a permutation search over ~62,000
word lists; `median-of-a-stream` against `statistics.median` at every prefix of
~140,000 streams; `water-flowing-to-both-oceans` against a forward downhill
search over 21,297 grids; `rebuild-a-tree-from-traversals` round-tripped through
every tree shape up to eight nodes. The oracles are usually the solutions the
prompts *ban* — `fnmatch`, `sorted(a) == sorted(b)`, sort-and-merge — which is
the point: two implementations that can only agree by both being right.

**One sweep had to be trimmed, which is the time limit doing its job on the
tests rather than on a solution.** `maximum-product-subarray`'s sweep over every
list up to length seven pushed that file to eight seconds against a ten-second
limit. Length six is a seventh of the cases and 3.3s — the kind of margin that
passes locally and fails on a loaded CI box, and the same hazard §11 records for
`-n auto`.

**A guard was added that the contract says is unreachable.**
`how-many-meeting-rooms` sweeps two sorted lists of endpoints, and a zero-width
meeting walks the pointer off the end of the ends list and raises. In-contract
input cannot do it — every meeting has positive duration, so something is always
still running when the next starts — and the exhaustive check found it anyway,
because degenerate intervals were in the pool. One comparison, kept: the
contract protects the caller, not the function.

**Two structural changes, both forced rather than chosen.** `trees-and-graphs`
split into `trees` and `graphs`: it held nine exercises of which four were
trees, seven more trees arrived at once, and a sixteen-exercise track mixing
binary trees with grid search teaches neither. `dynamic-programming` split by
dimension for a sharper reason than size — a linear recurrence is about what to
carry forward, a table is about *which neighbours the recurrence reads*, which
is what decides how far it can be collapsed, and those are different lessons.

**The curriculum was reordered, not appended to, and two of the orderings turned
out to be load-bearing.** Appending had produced a run of five consecutive kata
tracks — 43 katas before the next git exercise, which is exactly the fortnight
§15's interleaving rule exists to prevent. Strict alternation is no longer
possible and will not become possible: 14 kata tracks against 7 git and sql
ones, so the achievable bound is **two** kata tracks between non-kata ones, and
that is now written in the manifest header as the thing to re-check. Of the two
orderings that matter, `grids-and-matrices` now precedes `graphs` because
`clone-a-graph`'s notes argue against `find-a-word-in-a-grid` — a permanent
visited mark against one that is undone — and that was a forward reference;
`data-structure-design` is last among the katas because `find-words-in-a-grid`
composes the trie with that same grid search and needs both parents first.
`start-here` was not touched, so
`test_the_first_screen_of_the_curriculum_offers_every_kind` still holds.

**The content suite's critical path moved; the durations are not reportable.**
`tests/content/test_katas.py` has overtaken `test_scenarios.py` (~162s) as the
thing the pre-push suite waits for, because `--dist loadfile` puts a whole file
on one worker. That ranking is solid. The *numbers* are not: three serial runs
of that file on an idle machine gave **240s, 414s and ~500s**, and three runs of
the full gate gave **5m12s, 5m27s and 12m02s**. A 2.3x spread swamps anything 53
katas could contribute, so the first draft of this entry — which quoted 240s and
5m27s as facts and concluded "the total did not grow" — was asserting single
runs as measurements.

Worth recording as a finding in its own right, because it is the same error as
the tests this phase is about: **a number you observed once is not a
measurement.** It also re-reads §11's 7m20s baseline, which was presumably one
run too. ADR 0022's **Revisit if** now carries the range rather than a point,
and names splitting the sweeps into their own tier as the fix when they hurt.

**Final numbers, with one of them corrected on the way in.** 4,330 passing and
one skipped, 593 more than Phase 16. 100% statement and branch coverage over a
gated surface of **2,430 statements and 500 branches**, against Phase 16's
recorded 2,419 and 496.

That delta is **not** this phase's, and finding out why is worth recording. The
first draft of this entry attributed it to `practice validate`'s library audit
growing, which was a guess; `git diff` says the 53 katas changed nothing under
`src/` at all. The 11 statements and 4 branches come from a `Fix things` commit
that landed on main between the two phases and touched `domain/exercise.py`
among others — so the honest statement is that **this phase put nothing inside
the gate**, which is ADR 0004's content-as-data bet paying out for the fourth
consecutive time, and the gated surface moved for reasons belonging to another
commit. A handful of the 593 new tests come from there too; the rest are the
katas' parametrized content, library and pack cases, at four content tests per
kata plus the per-exercise library and pack sweeps.

`practice validate` reports 115 exercises, all valid; `practice fixtures
--check` reports 24 fixtures matching, unchanged, because no git fixture was
touched.

**What this bought, and what it did not.** It bought the library every technique
Blind 75 teaches, and tries, union-find, backtracking, bit manipulation and
heap-design where there had been nothing. It did **not** buy "NeetCode 150
complete", and the remaining ~87 are deliberately not scheduled: they are
additional reps inside families already covered eight deep, and on this phase's
evidence the expensive part of a kata is not the solution but the adversarial
test and the oracle that proves it discriminates. Another 87 of those is a far
larger commitment than the count suggests, and the gap-driven rule is the one to
re-apply rather than the list.

**2026-10-06 — Phase 18: the tutor context, and a feature that needed no new
tracking.** One session. The request was a way to ask an AI about the scenario
in progress, sketched as a JSON file recording actions as they happen with a
tutor prompt inside it. What shipped is a use case, a renderer and two
surfaces, and
[ADR 0023](adr/0023-the-tutor-context-is-what-the-solver-has-seen.md) has the
decision. The findings are below, in the order they turned up.

**The recorder already existed, so the phase was a projection.** `Attempt` has
kept every command with its exit code and output, and every hint with its index,
since Phase 1; `InspectRepository` has read the live repository through
`RepoQuery` since Phase 8. Both were built for other reasons — the process
assertions and the grade suggestion for the first, the repo state panel for the
second. `ExportTutorContext` takes the same four ports as `InspectRepository`
and adds no port, no adapter, no migration and no dependency. The one change to
code that already existed is `_view` becoming the public `view_of`.

**The reference solution was already unreachable, and the rest was not.** The
plan set out to keep the answer out of the bundle and found a third of the job
done: `KataSpec.reference` and `GitScenarioSpec.reference` are *filenames*, the
domain never holds a path, and no port a use case sees can open one. What an
`Exercise` does hold is every hint, the notes and the check list — so the
boundary had to be drawn in the DTO. `TutorContext` is the only type in
`application/dto.py` that does not carry the `Exercise` whole, and its docstring
says the module's own "thin on purpose" rule is being broken deliberately.

**The author's notes had never been shown to anyone.** Found while deciding
whether a post-mortem bundle should include them: `exercise.notes` is read in
exactly one place under `src/`, which is `validation.py` checking it is not
empty. 115 exercises have a `notes.md`, the README says the notes are "the
product", and no template and no CLI command prints one. The bundle for a graded
attempt is now the first place they appear. This is a gap in the product that
long predates the phase, and the phase only half closes it: the verdict page
still does not show the notes, and it should.

**`practice context | clip` would have raised on 96 of the 115 exercises.**
Python encodes a piped stdout in the console code page, cp1252 has no arrow and
96 `exercise.yaml` files hold a character it cannot write. It did not fail on
this machine, where stdout is UTF-8, which is exactly why it would have shipped.
The command now writes UTF-8 bytes itself when it is not on a console. That
fixes the half it controls: Windows PowerShell re-decodes a native command's
output in its own code page before `Set-Clipboard` sees it, so `--output FILE`
exists for the half it does not.

**The first test for that could not fail, and ADR 0022 is why it was caught.**
It ran the command under `CliRunner` and asserted the captured bytes decoded as
UTF-8 — which `CliRunner` guarantees whichever way the command writes, because
its fake stdout *is* UTF-8. The rewritten test runs under
`CliRunner(charset="cp1252")` against an exercise whose task holds an em dash,
and was then run against the bug: with the encoding left to the stream it fails
with `UnicodeDecodeError` on a lone `0x97`. Four mutations were run this phase
and all four were killed — that one, and three of the use case against the
library-wide suite (notes always: 115 failures; hints appended to the prompt:
230; the hidden suite read instead of the stub: 83).

**"Is not in the bundle" is a claim that cannot fail on its own.** The same
lesson in a second place. If the renderer wrapped a hint differently from how
the exercise stores it, `hint not in text` would pass for a bundle with every
hint printed in it. So `tests/content/test_tutor_context.py` pairs each absence
with a presence: the first hint is found verbatim once revealed, and the notes
and every check label once a verdict exists. Parametrized per kind rather than
skipped, which is `test_library.py`'s rule and was broken in the first draft
with 32 skip lines.

**Two things only pressing the button could find.** The asynchronous clipboard
API rejects in a document that is not focused, which is the ordinary state of
an embedded browser pane, so the handler tries `execCommand` next and failing
that leaves the text selected and says so. And `git push` to the fixture's
remote prints the remote's absolute path, which holds the Windows username; the
log records it and the bundle repeats it into a chat. The first is handled. The
second is recorded as a cost in ADR 0023 and in the README, and not fixed: the
place that could rewrite the path is the sandbox, and a renderer guessing at it
would be the wrong layer.

**What was verified and what was not.** Both surfaces were driven by hand
against real attempts: a git scenario through the CLI and the workbench, and a
kata in the workbench with source typed into CodeMirror and found in the
bundle. The copy button's *fallback* was observed. Its success path was not —
the pane it was pressed in never had focus — so "Copied." is untested by
anything but reading the code.

**The grade suggestion cannot see a tutor, and that is accepted.** A revealed
hint is recorded because the tool showed it; a copied bundle is not, because the
tool cannot know it was pasted. So a pass with a model's help is scheduled like
a pass. ADR 0023's first **Revisit if** names what would change that, and notes
that Phase 19's MCP server shifts the argument: a tool call is an event the
application can vouch for.

**Final numbers.** 4,967 passing and one skipped, 637 more than Phase 17 — 544
of them the library-wide boundary suite, at four cases per exercise plus one per
kata. 100% statement and branch coverage over a gated surface of **2,618
statements and 554 branches**, against Phase 17's 2,430 and 500 — and unlike the
last two phases the delta *is* this one's, all 188 statements of it:
`git diff` shows nothing else under `domain/` or `application/` since Phase 17
closed. `application/tutor.py`, `export_tutor_context.py`, the DTO and one
policy property are all inside the gate, which is where a spoiler boundary
belongs. `practice validate` reports 115 exercises, all valid, and `practice
fixtures --check` 24 fixtures matching — both unchanged, because no content was
touched. The gate itself took 15m29s, on one run, which by Phase 17's own
finding is not a measurement.

**2026-10-06 — Phase 19: the MCP server, and a read-only port that had one way
to write.** One session, the same day as Phase 18 and its second half.
`practice mcp` serves an open attempt to an AI client over stdio, with three
tools that read and none that runs a command.
[ADR 0024](adr/0024-an-mcp-server-that-can-only-read.md) has the decision. The
findings, in the order they turned up:

**The dependency was the risk the plan named, and it did not materialise for a
reason the plan could not have known.** The worry was `httpx`: the SDK was
expected to bring it, Starlette's `TestClient` warns when it is used, and
`filterwarnings = ["error"]` makes that a collection error. The SDK's 2.x line
depends on `httpx2`, which this project already uses. Importing it under
`-W error` is clean. Thirteen packages were added to `uv.lock` and no existing
pin moved.

**The same 2.x line had moved the API the plan was written against.** The
server class had been renamed and the client rewritten. The plan said to read
the installed package before writing against it, and that sentence was the only
part of the plan's MCP section that survived contact: every call here was
written from `site-packages`. The hand-rolled alternative ADR 0024 records was
rejected to avoid tracking a protocol's revisions, and what replaced it is
tracking an SDK's.

**The plan's `read_file` was the wrong shape, and `RepoQuery` was already the
right one.** The plan sketched a tool running "read-only" git commands through
the command policy. Whether `git branch` reads or writes depends on its
arguments, so that would have been a second, worse copy of git's option parser.
`RepoQuery` is a list of questions that are safe to ask, designed for
an unrelated reason — so that twenty assertions could be tested without git —
and `ReadAttemptFile` reaches a repository only through it.

**And then "read-only" turned out to be true of the port's contract and not of
its implementation.** `GitRepoQuery.read_blob` runs `git show <rev>:<path>`.
Every revision it had ever been handed came from an exercise
author, which is trusted content (§8.1). `ReadAttemptFile` is the first caller
whose revision comes from a model, and `git show --output=FILE` opens FILE for
writing. This was run against real git before being written anywhere, per ADR
0022: git answers *"could not open 'pwned.txt:README.md' for writing"*, failing
on Windows only because the colon in `<rev>:<path>` is not a legal filename
there. On Linux, where CI runs, it would have written the file. Two guards in
the use case — a leading hyphen is refused, and what reaches `read_blob` is the
hash `rev_parse` resolved rather than the caller's string — and three
mutations, all killed (no hyphen guard: 3 failures; the caller's string passed
through: 1; no allowlist for a kata's workspace: 6). **The adapter is
unchanged.** `--end-of-options` is the right fix there and git accepts it; it
is left for its own change because it alters the path every
`file_at_ref_matches` check is graded through.

**The first test of the missing-extra refusal was fitted to its own mock, and
it was the test failing that showed it.** `sys.modules["mcp"] = None` is the
usual way to stage a missing package. It raises *"No module named 'mcp.server';
'mcp' is not a package"*, naming the submodule; a real base install raises *"No
module named 'mcp'"*. The command compared the name to `"mcp"` exactly, so the
test failed for a reason no user could cause — and the tempting repair was to
loosen the command until the mock passed. The test now installs a meta path
finder that fails the way a missing package does. Same family as Phase 18's
`CliRunner` finding: a double that differs from the real thing in exactly the
property under test.

**ADR 0023's excuse for not recording a consult no longer holds.** It accepted
that asking a tutor is invisible to the grade suggestion because the tool
cannot know a copied bundle was pasted. Over MCP it can: a `get_context` call
is something the application can vouch for. The hole is left open here because
closing it makes the read path write, and it is the first item under ADR 0024's
**Revisit if**. Recorded as a decision deferred rather than one made.

**What was verified and what was not.** The server was driven three ways: in
process by the SDK's client over real services and real git; as a subprocess
over real stdio by the same client, in a test; and by hand through the exact
`uv run --no-sync --directory ... practice mcp` line the README gives, from a
different working directory. **It was not attached to Claude Desktop or Claude
Code**, so the README's configuration block is correct by the SDK's client and
by the protocol's handshake and has not been watched working in the client it
is written for.

**Final numbers.** 5,020 passing and one skipped, 53 more than Phase 18. 100%
statement and branch coverage over a gated surface of **2,676 statements and
578 branches**, against Phase 18's 2,618 and 554 — the delta is
`read_attempt_file.py` and its line in the package's exports, because the
server and the command are interface and sit outside the gate. Nothing under
`adapters/` changed. `practice validate` and `practice fixtures --check` are
unchanged. The gate took 11m56s against Phase 18's 15m29s, one run each, which
says nothing about either.

**2026-10-12 — Phase 20: tracks, a Next button, and a history nobody could ask
about.** One session, and the first phase that started from a complaint rather
than from §11's menu: *"this doesn't seem to have persistent memory."*
[ADR 0025](adr/0025-tracks-are-a-second-manifest.md) has the decisions. The
findings, in the order they turned up:

**The storage was fine, and that took an hour to establish for a reason that
had nothing to do with this project.** The database at the default path held
three applied migrations and no attempts, with workspaces on disk three days
newer than its last write. That reads exactly like a save path that silently
does nothing. It was not: the session doing the diagnosing was launched by an
MSIX-packaged desktop app, and Windows redirects such a process's writes under
`%LOCALAPPDATA%` to a private per-package copy. `os.path.realpath` on
`config.database_path()` named the copy. The server the solver actually runs,
started from a terminal, had ten attempts in the real file. **So the tool
remembered everything and showed none of it by exercise** — which is the
finding, and from the outside is indistinguishable from the bug that was
reported.

**The same redirection is a live defect in Phase 19 and is not fixed here.** An
MCP server launched by that desktop app resolves the same path to the same
private copy, so `list_attempts` answered "No attempt is open" while the real
server had one. ADR 0024 recorded that the server "was not attached to Claude
Desktop or Claude Code"; this is what attaching it found. The fix is a decision
about where the data directory lives on Windows — out from under AppData, or an
explicit `--database` in the client's configuration — and it moves somebody's
attempt history, so it is recorded as open rather than made in passing.

**"New" meant "has no card", and that was the tool forgetting.** A review card
is written when a schedule grade is pressed. An exercise solved and walked away
from therefore had no card, and the dashboard offered it as new a minute later.
`partials/review.html` had said so in as many words since Phase 9 — *"the cost
of skipping this is that the tool keeps no memory of the attempt"* — as a
defence of not scheduling automatically. The defence still holds for the
schedule. It never held for the label.

**Deriving a track's order from the curriculum was the plan, and running it is
what killed it.** A track as a set, walked in curriculum order, needs no
validation because there is only one order. Restricted to the seventy-five, it
reaches `contains-a-duplicate` tenth and puts four mediums at steps three to
six; for git, three mediums and a hard at three to six. The curriculum is right
interleaved and wrong filtered, because its on-ramps are often exercises a
selection leaves out. So tracks carry their own order, and the claim that an
order makes sense became a rule instead of a hope: `practice validate` refuses
a track that reverses two exercises inside one curriculum section.

**A test written for the tracks found a defect in the curriculum.**
`test_no_track_offers_a_lesson_before_its_premise` lists `(premise, lesson)`
pairs across sections and checks every track holding both. It was written
against the Blind 75's order. The whole-library track holds every pair, so it
ran against the curriculum too, and failed: `group-anagrams` — the character
count used as a dictionary key — came two sections before `is-it-an-anagram`,
the character count on its own. Phase 17 added the second and filed it where it
fitted rather than where it was needed. Moved; one line in `curriculum.yaml`.

**Three of the new tests were wrong about their own point, and the suite caught
all three at once**, which is ADR 0022's good half. A table row expected the
wrong message for an empty list; a pack fixture declared a track in an order the
new rule forbids, so the *validator* failed the test that was meant to show a
pack validating; and an assertion that one section was not nested in another
was arithmetic on tag counts that came out wrong. The last was replaced by the
one-line property it was reaching for.

**The full suite caught the one thing the fast tier could not, which is the
shape §11 predicts.** `test_an_installed_library_is_byte_identical_to_the_source`
compares every file of an installed pack against its source and skips the
derived indexes *by name*. A pack now writes a third one, `tracks.yaml`, so the
test failed with exactly that file in its list — in `tests/content`, a
directory the change had not touched, asserting on something `mypy` cannot see.
The fix is the name in the set; the claim it protects is unchanged, which is
that no *exercise* file may differ by a byte.

**A solver's history cannot be pushed, and that is now a test rather than a
habit.** The question was asked at the end of the session — the repository is
public and the attempt log is personal. It was already true twice over: the
database and the workspaces default to per-user directories outside the
checkout, and `.gitignore` covers a database kept beside the code anyway. But
neither was held by anything. `tests/integration/test_progress_stays_local.py`
asserts the defaults are outside the project root and asks `git check-ignore`
about thirteen places progress could land, with a control case so the question
is seen to have a no. Nothing in this phase stores anything new: a track's
progress is derived from attempts on every request.

**Not done, and worth saying.** No status *filter* on `/browse`, for the reason
the route gave in Phase 9. No local dates: `SystemClock` is UTC and so is every
date on every page, which for an evening attempt west of Greenwich is tomorrow.
An attempt resumed from the dashboard loses its track. And the CLI knows
nothing about tracks — `practice start` takes an exercise id, and "next" is a
web control.

**Final numbers.** 5,188 passing and one skipped. 100% statement and
branch coverage over a gated surface of **2,823 statements and
604 branches**, against Phase 19's 2,676 and 578 — the delta is
`domain/track.py`, `application/tracks.py` and the three use cases. One new
method on one existing port, no new port, no migration. `practice validate` now
audits `tracks.yaml` as well; `practice fixtures --check` is unchanged. The gate
took 5m48s, one run, which CLAUDE.md is right to say is not a measurement.

**2026-10-12 — After Phase 20: the current-attempt mark, built three times.**
Not a phase: one report from using Phase 19 — *"whenever I try the MCP, it
claims I have multiple attempts open"* — and the change that answers it.
[ADR 0026](adr/0026-the-current-attempt-is-a-mark-the-solver-leaves.md) has the
decision. What is worth keeping is how many times it was wrong on the way, and
what found each one.

**ADR 0024 priced the refusal at "one round trip" and it was every round
trip.** It was written for several attempts being open, as though that were
unusual. Abandoning an attempt is a deliberate act and leaving one is not, so
one unfinished exercise is the ordinary state of the database.

**The cheap answer could not be built, and reading one docstring said so.** The
open attempt with the most recent event needs no migration and no write.
`watch_solution_file.py` settled in Phase 10 that an editor save is not an
event (ADR 0013), so a kata has the same last activity after half an hour of
typing as when it was started, and "most recent" is "most recently started" for
most of the library. The mark had to be something the solver does.

**The first build marked on page load, and a question from the person it was
for took it apart**: *what happens if I have two problems open in different
tabs?* The mark sat with whichever page had loaded last, because switching tabs
makes no request. It had also made a GET write, which `security.py` rules out
in a sentence the cross-origin guard depends on. The suggestion that came with
the question — ask, at that point — is the behaviour one would want and cannot
be built: a page cannot keep asserting that it is open, because a browser
throttles, freezes and then discards a background tab. What a page *can* say
reliably is that it has come to the front, and that answers the question
instead of raising it.

**The second build passed the whole suite, 5,214 tests and a mutation run, and
a review of its own diff found ten things.** Three were the feature being
wrong. With one attempt left unfinished and another just submitted, the only
open attempt is the stale one, and a rule that looked at what was open handed
*that* to a tutor asked what went wrong — the exact situation in the report,
one step later. `practice submit` loads through `ResumeAttempt`, which marked,
so grading one attempt from a terminal took the mark from another. And a page
restored by the back button reruns no script and changes neither visibility nor
focus, so it never said it was in front. **None of the three could have failed
a test, because each test had been written from the same picture of the feature
as the code.** The mutation run proved the tests could see the code change; it
could not show that the code was the right code.

**So the third build has one writer and one reader.** `MarkCurrentAttempt` is
the only thing that sets the mark and is called by the three surfaces that put
an attempt in front of a person; `StartAttempt`, `ResumeAttempt`,
`ListOpenAttempts` and `OpenWorkbench` are byte-for-byte what they were before
any of this. `FindCurrentAttempt` holds the rule, and the rule lets a submitted
attempt keep the mark — which closes the hole and also retires ADR 0024's "pass
its id, which is in the workbench URL" for the commonest post-mortem there is.

**The page's script was tested by finding its text in the page.** Three
substrings, all present in a version with no answer to the back button. It is
now `static/in-front.js`, the first JavaScript of ours outside a template, and
`tests/web/test_in_front_script.py` runs it under node against a document that
is a list of events. That is ADR 0022's rule arriving somewhere it was not
written for: an assertion about code nobody executed is a guess. The cost is a
test that skips where node is not installed.

**What a deliberately broken copy found that review had not.** Thirty-four
mutations over the third build; one survived. Taking the `focus` listener back
off after a refusal changed nothing observable, because the flag that
de-duplicates reports was already holding the page silent. The four
`removeEventListener` calls became one flag, which cannot be half done.

**Left open, and recorded in the ADR as costs.** "Looked at last" is not "being
asked about": glance at the other tab and the tutor is shown it. A submitted
attempt holds the mark until something else is in front, so the next morning's
question is answered from yesterday's verdict. A fourth surface that puts an
attempt in front of somebody has to remember to say so. And none of it has been
exercised by a real tab switch — the browser available to the session that
built it keeps its pane hidden, so visibility was simulated there and in node.
The MSIX redirection Phase 20 recorded is still open and still decides whether
an MCP client sees any of this.

**A second review, of the commits, found five more, and the first is the one a
user would have met.** Nothing is marked on the day this arrives: an existing
database has several attempts open and an empty table, and a tab open across
the upgrade has no script in it. So the first question after upgrading gets the
refusal the change exists to remove — and the README said that could only
happen after abandoning an attempt. It is a cost rather than a bug, since no
migration could have chosen for the solver, and it is now said where it will be
read first. The others: the script's tests skipped without node *on the runner
too*, on the strength of a sentence in the ADR that nothing held, so under `CI`
they now fail instead; `practice attempts` said nothing when the current
attempt was a finished one; `practice resume` marked before a check that can
turn it away; and `FindCurrentAttempt` loaded the open attempts its three
callers had each just listed, so it is handed them.

**Final numbers.** 5,242 passing and one skipped. 100% statement and branch
coverage over a gated surface of **2,862 statements and 616 branches**, against
Phase 20's 2,823 and 604 — the delta is the two use cases and their wiring. Two
new methods on one existing port, no new port, one migration. Twenty-four use
cases where there were twenty-two. `practice validate` and `practice fixtures
--check` are unchanged. The gate took 6m11s, one run.

**2026-10-12 — Phase 21: statements you can check, and the interviewer's
follow-up.** Two requests from using the library — *proper constraints, a good
lookover, an examples tab*, and then *variants like they do in interviews* —
taken as one phase because the second is authored in the first one's format.
[ADR 0027](adr/0027-examples-are-source-run-against-the-reference.md) and
[ADR 0028](adr/0028-a-variant-is-a-whole-exercise-offered-under-its-base.md)
have the decisions. What follows is what the work found.

**The examples had never been run, and every one was right.** Eighty-three
prompts carried their examples as aligned text in a fence. Moving them into
`examples:` as executable source and running each against its reference found
no wrong value among the ones that already existed — which is a result, since
nothing before this could have said so. The check itself was then run against
four deliberate corruptions (a wrong value, `1` for `True`, a list for a tuple,
a tree of the wrong shape) and failed on each, by name. ADR 0022's rule,
applied to the page.

**Constraints were derived from the suites, and that is what found the prose
problems.** A scratch probe wrapped each reference, ran its hidden suite and
recorded the shape of every argument: lengths, value ranges, emptiness,
repeats. Every stated bound is at or above what was observed. Held against
that, three kinds of prompt turned out to be wrong in ways reading had not
shown:

- one promised an input the suite never passes
  (`serialize-and-deserialize-a-tree`, "a chain a thousand deep"; the deepest is
  four nodes);
- three were tested on behaviour they never mentioned — an empty string in
  `find-words-in-a-grid`'s word list, an edge from a node to itself in the two
  union-find katas;
- and `meeting-rooms` and `how-many-meeting-rooms` were **the same problem**,
  same title, same function name. The first predates the Blind 75 fill-in that
  added the second. It is now the question the list has in that slot — can one
  person attend them all — with a suite that kills six wrong solutions,
  including the neighbour-comparison that forgets to sort.

**The deviation: constraints are stated, not enforced.** The examples are
checked on every run; the constraints were checked once, by a script that is
not in the repository. The enforced form was designed and not built (ADR 0027
has why), and CLAUDE.md now says to check the bound when adding a test.

**Variants were first designed as a mode of the attempt, and that design was
thrown away before any of it was written.** It needed a column, a migration, a
second path through the provisioner and the grader, and a relaxation of
`validate_filename`'s bare-name rule. A variant as a whole exercise that is
*never listed* needed one port method, one use case and a select. The measure
of the difference: a dozen callers enumerate the library, and none of them
changed. `ReviewQueue` changed by one lookup, so that a variant a solver chose
to attempt comes due like anything else and one nobody has tried is never
offered.

**"The base's solution must fail it" shaped the content before it existed.**
The first variant drafted was Two Sum on a sorted list with `O(1)` extra space
— and the standard dict solution passes that, because nothing observes memory.
The check would have rejected the variant as its base listed twice. So the
variant returns 1-based positions, as the well-known version of it does, and
its suite measures allocation with `tracemalloc`: the dict solution now fails
on exactly the claim the twist makes.

**Forty-five wrong solutions, no survivors.** Each variant's suite was run
against between two and five mutants written for it — the standard answer
carried over, the tempting generalisation, the off-by-one at the boundary, the
quadratic version — and every one failed, six of them on the time limit alone.
One expected value in a draft suite was wrong (`"abcdba"` *is* one deletion
from a palindrome) and was caught on re-reading before it ran; the reference
would have disagreed.

**The suite's floor did not move.** Variants are graded by
`tests/content/test_variants.py`, which imports `test_katas.py`'s tests and
overrides the directories they walk, so under `--dist loadfile` the fourteen
run beside the eighty-three rather than after them.

**Not done, and worth saying.** Sixty-nine katas have no variant; the select
simply does not appear for them. Packs do not carry variants. An attempt at a
variant counts in the activity chart and not in tag mastery. There are no
variants of scenarios or drills, though nothing in the domain forbids them. And
`practice solve` has no `--variant`: only `start` does.

**Final numbers.** 5,850 passing and one skipped. 100% statement and branch
coverage over a gated surface of **2,933 statements and 644 branches**, against
2,862 and 616 before — the delta is `Example`, `Variant`, `Exercise.statement`
and `ChooseVersion`. One new method on one existing port, one new port
(`Chooser`, with a real adapter and a fake), no migration. Twenty-five use cases
where there were twenty-four. `practice validate` reports 129 exercises — the
115 the library lists and 14 variants — and now audits a variant's base;
`practice fixtures --check` is unchanged. The gate took 10m31s and then 9m55s:
two runs, the first with the one failure this phase's own change caused
(`test_the_repository_loads_the_whole_library` compared the listing with the
walk, and a variant is in the second and not the first). That is slower than
Phase 20's 6m11s and, on CLAUDE.md's own evidence about this machine, not yet
a measurement of anything: `test_variants.py` runs beside `test_katas.py`, but
it is a fifth long file on four workers.

**2026-10-12 — Phase 21, continued: a variant for every kata.** The first
tranche left sixty-nine katas without one. They have one now — eighty-three
variants, one per kata — and
`tests/content/test_library.py::test_every_kata_offers_a_variant` holds the
claim. Nothing in `src/` changed for it, which is ADR 0028's bet paying out:
sixty-nine exercises were added as data.

**The twists fall into a few kinds, and it is worth knowing which.** A changed
*question* over the same structure (count the ways, return the bounds, list
them all, the kth largest rather than the kth smallest). A changed
*convention* (half-open intervals, eight neighbours, repeats allowed on one
side, ties by arrival). *More structure* in the input that the standard answer
ignores (sorted, a search tree, all positive). And a *generalisation* that
breaks an optimisation the special case allowed (any step sizes, a reach of
k, a wider alarm on the circle). The last kind produced the best material:
several of the standard katas' reference solutions rely on something their
variant takes away.

**Two hundred and nineteen wrong solutions were run against the suites, and
the four that survived were the useful part.**

- *Two were right, and my notes were wrong.* The spiral builder's reference
  had two guards "for the centre of an odd square"; the longest-word search
  had a letter count "for speed". A solution without either passed. A square's
  rings close on all four sides at once, so the guards never fire; and the
  search was never slow at the stated size, which is ADR 0022's "an asymptotic
  argument is not a performance claim until the constant is measured" again,
  word for word. The code, the hints and the notes all said otherwise and all
  three were corrected.
- *One was a hole.* A plain set of words passed the removable trie's suite,
  because nothing asked `starts_with` for a prefix nobody has, twenty thousand
  times, against fifty thousand words. That test exists now.
- *One was a bad mutant*, correct by accident, and was deleted.

**Four expected values were wrong as first written**, all caught on re-reading
before the suite ran: a decoding that does not exist, a valley described as a
peak, an interval off by one, a garbled example. The content suite catches
that class reliably. It could not have caught the three above.

**The cost is in the gate.** `test_variants.py` is now as long as
`test_katas.py`. Under `--dist loadfile` they run side by side, so the suite
has two critical paths rather than one of twice the length, but the fourth
worker is no longer spare.

**Not done.** One variant per kata, where several would be natural. No
variants of scenarios or drills. Packs still do not carry them, and
`practice solve` still has no `--variant`.

**Final numbers.** 7,162 passing and one skipped, where the first
tranche ended on 5,850: the 1,312 between them are nineteen tests for each of
sixty-nine variants, and the one that requires a variant of every kata. 100%
statement and branch coverage over 2,933
statements and 644 branches, both unchanged, because no line under `src/` was
touched. `practice validate` reports 198 exercises — the 115 the library lists
and 83 variants; `practice fixtures --check` is unchanged. The gate took
10m05s, one run, clean. The first tranche's two runs were 10m31s and 9m55s
with a sixth as many variants, which says that this machine's noise is wider
than the cost of sixty-nine more, and nothing more precise than that.
