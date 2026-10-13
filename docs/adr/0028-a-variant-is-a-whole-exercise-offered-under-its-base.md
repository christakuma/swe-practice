# 0028 — A variant is a whole exercise, offered under the one it varies

- **Status:** accepted
- **Date:** 2026-10-12
- **Phase:** after Phase 20 (variants)

## Context

The request: *options under each question — slight modifications to the problem
to mess you up like they do in interviews. Keep the default version of each
problem, but allow the user to select variations or get random versions.*

The interviewer's follow-up is a real and specific thing. The list is sorted
now. Return how many ways instead of the fewest. The houses are in a circle.
What makes it hard is not the new problem but the old solution: the familiar
answer is already in your fingers, and the twist is aimed at exactly that.

Three things constrained the design.

**A twist is a different problem to grade.** A new prompt, new constraints, new
examples, usually a new signature, always a new hidden suite and a new
reference. Nothing about the base's files can be reused except its name.

**An attempt is the unit everything else is built on.** Provisioning, the
policy, grading, the event log, resuming, the tutor export, the MCP server and
review scheduling all take an exercise id and an attempt id and nothing else.

**The library is listed in a dozen places**, and each one means "the problems
on offer": Browse, the dashboard queue, every track, the curriculum, the
progress totals, `practice list`, the pack builder. A twist on Two Sum is not a
sixteenth array problem to work through in order.

## Decision

**A variant is an exercise with a `variant:` block.**

```yaml
id: variants/two-sum-in-a-sorted-list
variant:
  of: katas/two-sum
  twist: "The list is sorted, you get O(1) extra space, and positions count from 1."
```

It lives in its own directory under `content/variants/`, with its own
`exercise.yaml`, stub, tests, reference and notes, and is loaded, validated and
graded like any other kata.

**It is never listed.** `ContentRepository.list_exercises` leaves variants out,
so the curriculum does not place them, no track names them, and no count of the
library includes them. A new port method, `variants_of(exercise_id)`, is the
only way one is offered, and `get(id)` still finds one — which is all an
attempt has ever needed.

**Choosing a version resolves to an id before anything is started.**
`ChooseVersion(exercise_id, choice)` returns the base's id for no choice, a
variant's id for its name, and for `random` a draw among *all* versions, the
standard one included. `StartAttempt` is then called with that id and is
unchanged. Chance is a port (`Chooser`) with one real adapter over
`random.choice`.

**Three surfaces offer the choice.** The Start control gains a select —
Standard, each variant, Surprise me — only for an exercise that has variants.
`practice start --variant <name|random>` does the same from a terminal. A
variant's workbench says what the twist is above both columns, which after a
draw is how a solver learns what came up.

**`practice validate` holds three library-level rules**: a variant's base
exists, is not itself a variant, and is the same kind. Naming a variant in the
curriculum or a track fails as naming something that is not there to be placed.

**The content suite holds a variant to everything a kata is held to, and one
thing more: its base's reference solution must fail it.** A twist the standard
answer already satisfies is the same exercise listed twice.

## Consequences

**Almost nothing downstream changed.** A variant is provisioned, graded,
resumed, tutored and exported by code that existed and was tested. The
application layer's whole footprint is one use case of forty lines; the web
layer's is a select, a form field and a note.

**No migration.** Nothing new is stored on an attempt. An attempt at a variant
has the variant's exercise id, and that is the record.

**A variant has its own review card**, because a card is keyed by exercise id.
It never appears in the queue's unseen half — it is not in the listing — and
comes due like anything else once a solver has chosen to attempt it. That is
the behaviour wanted, and it cost one changed lookup in `ReviewQueue`.

**Progress does not count variants toward tag mastery.** `SummariseProgress`
builds its exercise table from the listing, so an attempt at a variant shows in
the activity chart and not in the mastery one. Arguably right — the tags
describe the curriculum — and not something this decision chose so much as
inherited.

**Packs do not carry variants.** A pack is built from the listing and read back
through its curriculum, and a variant is in neither.
`PackContentRepository.variants_of` returns nothing. Sharing a twist would be a
change to the archive format and to what `install_pack` checks.

**The variants are graded beside the katas, not after them, and that took a
decision.** Every variant costs four grading subprocesses. Parametrising
`test_katas.py` over them would have doubled the file that is already the
critical path under `--dist loadfile`, so they are graded by
`test_variants.py`, which imports the same tests and fixtures and overrides
which directories they walk. With a variant for every kata that file is now
as long as the one it sits beside: the suite has two critical paths rather
than one twice the length.

**Every one of the eighty-three katas has a variant**, one each, chosen for a
twist that changes the algorithm or a convention rather than the wording:
sorted input, a circular list, count instead of decide, a flipped endpoint
rule, eight neighbours instead of four. `tests/content/test_library.py` holds
that claim, so a kata added later without one fails.

Each was written with a brute-force oracle swept over every small input, and
each suite was then run against deliberately wrong solutions written for it —
**219 in all**. Four survived on first contact, and what they turned out to be
is the argument for doing it:

- two were not wrong. The reference for the spiral builder carried two guards
  "for the centre of an odd square", and the longest-word search a letter
  count "for speed". A version without either passed, because a square's rings
  close on all four sides at once and the search was never slow. Both claims
  were mine, both were in the notes, and both were false;
- one was a hole in a suite: a plain set of words passed the removable trie's
  tests, because nothing held `starts_with` to being independent of how many
  words are stored. That test now exists;
- one was a badly written mutant.

Nothing but running them would have found the first three.

## Alternatives considered

**A variant as a mode of its base**, stored on the attempt: `Attempt.variant`,
resolved to a second set of files beside the first. This is what the word
suggests and it was the first design. Rejected on what it touches:

- a new column on every stored attempt, and a migration;
- a second path through the provisioner and the kata grader, to copy and run a
  different stub and suite;
- a relaxation of `validate_filename`'s bare-name rule, which exists because a
  spec filename is resolved against two roots and a path escapes both, in order
  to reach `variants/sorted/tests.py`;
- a second copy of every content test, since a kata's variant files would be
  reachable only through the kata;
- every reader of an attempt — the workbench, the tutor, the MCP server —
  learning to ask which version it was.

All of it to arrive at something a solver cannot distinguish from an exercise.

**Variants as ordinary katas with a tag.** No code at all, and they would be
rows in Browse, lines in the curriculum, and members of the katas track — a
library half again as long in which every problem is followed by a near-copy of
itself. The request was for options *under* each question.

**Random draws among the variants only.** Rejected because of the solver with
one variant: "surprise me" would then tell them exactly what was coming. An
interviewer's twist is only a twist if the problem as written was a possible
outcome.

**A generic `Chooser[T]`.** The port takes exercise ids. The one thing this
application leaves to chance is which version comes up, and a port shaped like
`random.choice` would be an invitation to find it a second job.

**Deriving a variant's prompt from its base** — a `twist` applied to the base's
text. A variant changes the constraints and the examples, often the return
value and sometimes the signature, and a prompt assembled from two files is a
prompt nobody has read as the solver will.

## Revisit if

- Somebody wants to share variants. That is a pack format change, and the
  point at which `variants_of` on the packed repository stops returning
  nothing.
- Variants of scenarios or drills are written. Nothing in the domain or the
  schema stops it; the content suite's "base's reference must fail" check is
  written for katas and would need a sibling.
- The mastery chart is wanted for variants. `SummariseProgress` would need the
  variants as well as the listing, which `variants_of` can supply per exercise.
- The variant count grows until `test_variants.py` is the critical path. The
  fix is the one CLAUDE.md already names for the exhaustive sweeps: a marked
  tier, argued for rather than drifted into.

## Addendum, 2026-10-13 — second variants, and the file that grades them

*"One each" stopped being true, and the last trigger above fired.* Seventy-nine
katas now have a second variant, 162 in all (PLAN.md §16 has the account).
Nothing in the decision changed and nothing under `src/` was touched: the
select, `--variant` and the draw were written for *each variant*, not for
*the* variant, and a second one is one more directory.

**The trigger was met with a narrower fix than the one named.** A marked
tier trades coverage per run for time. What had actually grown was one
*file*, and under `--dist loadfile` the longest file is the floor. So the
variants are dealt alternately between `test_variants.py` and
`test_variants_second_shard.py`, each no longer than `test_katas.py`, with a
test that the two shares add up to every variant. Everything is still graded
on every run. The marked tier remains the answer if the total, rather than
the longest file, becomes the cost.

**One rule was added for a second variant, and only by convention**: it must
be a different twist from its sibling, not a harder version of it. The suite
checks a variant against its base's reference and not against the other
variant's, because two variants of one kata usually differ in name or
signature and the check would be an `ImportError` proving nothing.
