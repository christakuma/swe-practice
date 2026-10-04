# Postmortem

Written at v1.0.0, after twelve phases, 98 commits, 3,138 passing tests and 54
exercises. The interesting half of a postmortem is the part that is not a
humble-brag, so the structure is: what the bet was, whether it paid, and the six
things that would be done differently — three of them things that worked and
would still be changed.

PLAN.md §16 is the contemporaneous record and is more reliable than this file
about *when* anything happened. This is the view from the end.

---

## The bet

> **Grade the end state, not the answer text.**

A git exercise builds a real repository with a real problem in it, the solver
runs real git, and grading inspects the resulting repository against declarative
assertions. The whole project is an argument that this is better than matching
command text, and the test of it is one verdict: `git reset --hard HEAD~1 &&
git push --force` produces files byte-identical to a correct `git revert`, and
the tool tells them apart on ancestry.

**It paid, and it paid earlier than expected.** The flagship scenario was
authored and run by hand against real git *before Phase 0 existed*, specifically
to find out whether the assertion vocabulary could express it. It could, with no
additions — and the same afternoon found four things that thinking about it had
not: the pinned clock covered only the fixture, the plan's own example was
missing a check it needed, the resolution grammar was unspecified, and `@c2`
syntax does not work in a solution file. Three of those four were invisible on
paper and obvious within a minute of running the thing.

That is the single most useful thing in this whole record: **the spike before
the plan.** Everything expensive that was avoided here was avoided by it.

## What the architecture bought, concretely

Not "it was clean". Three specific returns, each of which can be pointed at:

- **The `RepoQuery` port made 20 assertions testable with no git installed.**
  Implemented twice — real git, in-memory fake — unit-tested against the fake in
  milliseconds, with a conformance suite proving the two agree. That conformance
  suite is the only thing that makes the fast tests evidence about anything, and
  it is the part most likely to be skipped by someone copying the pattern.
- **Content as data meant Phase 11 was 51 exercises and three code commits.** The
  payoff of §5, and it very nearly held: the three code commits were each a case
  of content finding a real gap in the engine, which is the right kind of churn.
- **Phases 7 through 10 added three new ways to use the tool without touching
  the domain.** A browser, a scenario console, an own-editor mode. Each was an
  adapter. That is the actual test of whether a boundary earned its keep, and it
  is a test the boundary passed three times.

## What would be done differently

### 1. The per-commit greenness rule should have been priced before it was adopted

It was adopted at Phase 0 because it sounds unarguable, and it was removed at
Phase 11 because it cost over an hour of wall clock per phase and **could not
see a content commit at all** — so it had already stopped holding for seven of
that phase's thirteen commits while still being claimed. ([ADR
0015](adr/0015-verify-on-the-working-tree-not-every-commit.md).)

The mistake is not the rule. It is that a process rule was adopted without
anyone asking what it would cost at the size the project was *going* to be. The
same question asked about the architecture — "what does this cost when there are
fifty of them?" — was never asked about the verification process.

### 2. The suite was never measured until it hurt

When Phase 11 finally ran `pytest --durations=40`, **nine tests in one file were
27% of the suite**: tests that needed a library they could break had copied the
whole shipped one, so 54 exercises were being fingerprinted nine times over. At
two scenarios that cost seconds and nobody noticed. At twenty-four it was five
minutes.

The shape to watch for is in that sentence: **a cost that is invisible at the
size the test was written for and linear in content the test does not care
about.** Measuring took ten minutes and recovered seven. It should have been a
habit from Phase 3, not a reaction at Phase 11.

### 3. Three decisions were made in the plan that could only be made by building

Three things in PLAN.md were written with confidence and then corrected by
contact with reality, and all three were architectural rather than technical:

- `solution.sh` as a bash script, which validated reference solutions through an
  execution path the user cannot use — proving a solution existed, not that one
  existed *within the rules*. A scenario could have shipped unsolvable with a
  green build.
- `Attempt` holding an `ExerciseId` rather than a policy, so it had no access to
  the limits it was supposed to enforce.
- The check functions placed under `adapters/`, which put the most
  correctness-critical code in the project outside the coverage gate.

All three were caught in a review pass *before* Phase 0. The lesson is not "plan
less" — the plan is why the spike happened and why Phase 11 was mostly
authoring. It is that **the parts of a plan that describe a boundary are the
parts most worth attacking before writing code**, because the technical errors
are cheap (look up the API, fix the line) and the boundary errors would all have
survived to Phase 11 before doing visible damage.

### 4. Two assertions shipped flagged as "unproven", and that was the right call badly executed

`reflog_contains` and `command_count` were shipped in Phase 5 with a note saying
they would be deleted if Phase 11 did not use them. Phase 11 did not, and they
were deleted along with a port method and a value object. The rule worked.

What would change is the *shipping*. Flagging them meant writing them, testing
them, documenting them in the authoring guide, and holding them through six
phases — then deleting all of it. **Not writing them would have cost nothing and
risked nothing**, because the vocabulary has been extended before and the
extension is cheap. "Build it and mark it provisional" is a worse default than
"do not build it until something wants it", and this project has the data to say
so.

### 5. `practice up` should have existed at Phase 7

Phase 7's exit criterion was *a kata solved entirely in the browser*, and
nothing in the shipped CLI could open a browser at anything — `serve` is in no
commit list because nobody noticed it was needed until the phase would not
otherwise work. The same omission happened at Phase 6 with `practice start`.
Phase 12 is the third instance: the thing a *user* runs kept being left out of
plans that were otherwise careful.

A commit list can be in perfect dependency order and still describe a product
with no way into the state it adds. The missing step, every time, was asking
"what does somebody type to see this?" — which is the question the exit
criterion was already asking, phrased so that the plan could not answer it by
accident.

### 6. Windows was de-risked correctly, and the estimate was still wrong

§13 called Windows subprocess and path bugs the highest risk and budgeted six
sessions for Phase 3 instead of four. Phase 3 came in on the estimate — but
**not where the estimate expected it**. The Windows papercuts each cost minutes
rather than the forecast hour, because a fifteen-minute spike found them before
any module existed. The time went instead on semantics nobody had written down,
and on splitting the work into commits that each stood alone.

The useful generalisation: a risk you have named is usually not the one that
costs you, because naming it is most of the mitigation. The cost lands on the
things nobody wrote down — and the way to find those is, again, to run something.

## Things that are still wrong

Stated plainly, because the alternative is pretending v1.0.0 is finished:

- **The longest file sets the floor for the whole suite.** `--dist loadfile`
  puts every test in a file on one worker, which is what lets the content suite
  share its workspaces — and it means `test_scenarios.py`, at 138 seconds,
  decides how fast a 7m20s run can be. `--dist loadgroup` with a group per
  `(module, exercise)` would balance far better; it needs a
  `pytest_collection_modifyitems` hook, and that is the next lever if the suite
  becomes a problem again.
- **The demo can go stale without anything failing.** Deliberate ([ADR
  0016](adr/0016-a-generated-demo-not-a-recorded-one.md)), and still a thing
  that can be wrong in the README while the build is green.
- **An advisory check prints its label even when it fails**, so "You did not
  force-update a shared branch" appears above the evidence that you did. The
  label describes the passing state and the marker carries the verdict. It reads
  wrongly in exactly the output this project puts in its README.
- **No `rebase -i` content**, and the mechanism for it is fully worked out in
  §15 — two editor stand-ins, a `rebase_in_progress` assertion, and a plan file
  the solver writes. Parked for appetite, not for difficulty.
- **One `Scheduler` implementation in production.** SM-2 is behind a port with
  FSRS named as the second implementation (ADR 0008), and the port therefore
  meets §13's two-implementation rule only by counting its test double. It is
  the weakest instance of that rule in the project.

  **Resolved in Phase 13** ([ADR
  0018](adr/0018-fsrs-as-a-second-scheduler-not-a-replacement.md)). The text
  above is left as it was written, because the useful half of a postmortem is
  what was believed at the time — and because this is the one item on the list
  that was fixed by doing exactly what the list said was missing. What it got
  wrong is interesting: it framed this as a *rule-compliance* problem, and the
  payoff turned out to be a defect and two wrong beliefs. Writing the second
  implementation found a meaningless number on a page no fragment assertion
  could have caught, and showed that one of the four scheduler properties
  PLAN.md §9.7 states is SM-2's policy rather than a law. **A port with one
  implementation is not an unproven abstraction; it is a set of untested claims
  about what is general**, which is a worse thing and was not what this bullet
  said.

## The one-sentence version

The two things that paid for themselves many times over were **running a real
exercise against real git before writing any code** and **a test that fails the
build when a dependency arrow points the wrong way**; the two that cost most
were **a process rule nobody priced** and **a test suite nobody measured**, and
both of those are the same mistake — assuming that something cheap at three
exercises is cheap at fifty-four.
