# 0035 — A kata declares its signature, and the bounds it declares are enforced

- **Status:** accepted
- **Date:** 2026-10-26
- **Phase:** 28

## Context

A kata said what it takes and gives in three places that nothing tied together:
the stub's docstring (`Args:` / `Returns:`), the prose prompt, and a free-text
`constraints:` list. The first two could drift from the code a solver was
handed; the third was the one [ADR 0022](0022-counter-examples-are-run-against-the-bug-they-name.md)
was about -- a constraint is a promise about the inputs the hidden suite passes,
and a new test that stepped outside a stated bound failed nothing.

Across all 245 katas (83 listed, 162 variants) there were 721 constraint lines.
The anchored drafting patterns (`lo <= len(x) <= hi`, `lo <= x[i] <= hi`,
`lo <= x <= hi`, a node-count sentence, a rows-and-columns pair) mapped 463
bounds to ranges a machine can check; 369 lines stayed prose that no range
expresses: "all values are distinct", "an empty tree is None", "at most 2 * 10**5
calls are made".

And the stubs were uniform enough to read mechanically: every `Args:` and
`Returns:` followed one Google-style shape, 230 of 245 had exactly one function
to implement, and 9 had one class.

## Decision

1. **`kata.signature` is required and structured.** `functions:` and/or
   `classes:` (with `methods:`), each callable declaring `name`, `summary`,
   `parameters` (name, type, description), `returns` and optional `details` and
   `raises`. A kata without one does not load, so `practice validate` rejects it.
2. **Four measures, each a range.** A parameter may bound its `length`, the
   `item_length` of each element, the integers it `values` holds (however deeply
   nested), and the `nodes` reachable from it. That is what the hidden suites'
   bounds actually were. A bound is an integer or a string of integer
   arithmetic (`2 * 10**5`) and **keeps the author's spelling** for the page.
3. **`constraints:` is gone as a key.** The list the page shows is derived: the
   ranges, in declaration order, then `notes:`, which holds what a range cannot
   say and is printed but never checked. A kata with both lists would have two
   things to keep in step.
4. **The page's Input / Output header, the constraints and the stub docstrings
   are all derived from the one structure.** `Exercise.statement` carries the
   header too, so `practice solve` and the tutor export say what the page says.
   `tools/migrate_katas.py --stubs` regenerates the docstrings; a content test
   compares them verbatim.
5. **The bounds are enforced from inside the reference solution.**
   `tests/content/bounds_probe.py` is appended to the reference as a footer that
   wraps every declared callable and raises `AssertionError("DECLARED BOUND
   BROKEN: ...")` on an argument outside its ranges. `test_katas.py` grades the
   reference *with the footer armed* in the test it already had, so the check
   costs no additional subprocess.
6. **Stub and reference are held to the declaration by AST**: names, parameter
   order and, for the stub, every annotation.

## Consequences

- A hidden suite that steps outside its stated bound fails the build, naming the
  argument. The check found real disagreements on the day it landed (see PLAN.md
  §16).
- **Only ranges are checked.** "All values are distinct" and "the list is
  sorted" are still notes. The structure makes the checked part findable -- a
  note is a visible admission that a claim is unenforced -- but it does not
  shrink the notes to nothing, and roughly 360 lines stayed notes.
- The probe walks arguments through `list.__iter__` and `list.__len__`, never
  the instance's own, because `Tripwire` and `Watched` are `list` subclasses
  whose whole job is to object to being looked at. That is a subtle coupling
  between the probe and the hidden suites' test doubles.
- Only the outermost call is checked, so a recursive reference's helper
  arguments are not mistaken for suite inputs. A bound on a *helper's*
  arguments cannot be declared, which is correct.
- `prompt:` was **not** rewritten to drop its restatement of the signature.
  That is 245 prose edits whose correctness a machine cannot check and a person
  would have to read one by one; the generated header now sits beside the story
  and the restatement is a follow-up that removes text rather than adds it.
- Authoring a kata is more typing than it was: a signature is longer than a
  docstring. The migration drafted all 245, and the template is the cost saver
  going forward.

## Alternatives considered

- **Tidy the free-text format by hand.** The closest to winning, because it
  needs no schema. Rejected because it leaves `constraints:` unenforceable --
  the thing ADR 0022 found -- and a hand-tidy of 721 lines has no way to say it
  is done.
- **Parse constraints out of the prose.** Works on the 271 well-formed lines and
  is silently wrong about the rest: a regex confident about a constraint it
  misread is a bound the suite is held to that nobody wrote. The migration does
  use anchored patterns, once, to *draft*; the result is data a person reviews,
  not a parser that runs at load.
- **A general constraint expression language** (`all(-10**9 <= x <= 10**9 for x
  in numbers)`). Maximally flexible, and it makes the page print Python and the
  schema an evaluator. Four measures cover what was measured, and the fifth is
  a `notes:` line until a kata needs it.
- **A conftest plugin that records and replays arguments.** Needs a second
  process boundary and a file written inside a sandbox that is disposed before
  the test can read it. Raising from inside the call needs neither.
- **A separate bounds test per kata.** A second subprocess per kata, in the file
  that is already the suite's critical path (CLAUDE.md). Folding the check into
  the reference-passes test costs the footer's overhead and nothing else.
- **Annotations from the stub only, no `type:` field.** Rejected because a type
  the page prints should be the one the author wrote, and because the AST check
  is only a check if there are two things to compare.

## Revisit if

- A kind other than a kata grows a function signature -- the structure is
  Python-callable-shaped, and generalising it is a design, not a rename.
- A fifth measure is needed by more than a handful of katas ("all distinct",
  "sorted" are the candidates), at which point a `rules:` list with a small
  fixed vocabulary is cheaper than prose.
- The wrapper's overhead shows up in a kata's time limit. None did at landing.
