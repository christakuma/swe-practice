# 0004 — Content is declarative data, validated by schema

- **Status:** accepted
- **Date:** 2026-09-30
- **Phase:** 2

## Context

[ADR 0003](0003-grade-git-exercises-by-repo-state.md) commits the project to
grading the end state of a real repository against declarative assertions. That
decides *how* an exercise is graded. It leaves open the question this record
answers: **where does an exercise live, and what has to happen to add one?**

The constraint is not technical. It is that the project has a single, very
likely way to fail, and PLAN.md §13 names it as the highest-likelihood risk on
the list: **content authoring stalls.** A grading engine with eight exercises
is a demo. The value is in seventy, and seventy only happens if adding the
seventy-first is cheap enough to do on a Tuesday evening.

So the question is what the marginal cost of an exercise is. If authoring one
means writing Python — a class, a registry entry, a test module — then every
exercise carries the full weight of a code change: a review, a merge, a place
in an import graph, and the quiet friction of having to be in a programming
frame of mind to write what is essentially a teaching artefact. That cost is
paid seventy times, and the library stops at eight.

There is a second constraint pulling the other way. Data that nothing validates
is worse than code, not better. A typo'd field name in Python fails at import;
a typo'd field name in YAML is a silent default. An exercise that still loads
and still grades, just with one fewer constraint than its author wrote, is a
failure that reports green — which is the same shape as the "assertions too
loose to tell right from wrong" risk that ADR 0003 introduced.

## Decision

**An exercise is a directory of declarative data, and adding one requires zero
code changes.**

```
content/git/revert-a-pushed-commit/
  exercise.yaml        metadata, prompt, hints, and the checks
  fixture.sh           builds the broken repo (trusted bash)
  solution.cmds        reference — a command list, not a script
  naive-*.cmds         plausible wrong answers, each declaring what it must fail
  notes.md             revealed after grading
```

`exercise.yaml` is validated by Pydantic v2 models in
`adapters/content/schema.py`, and the schema is strict in four specific ways,
each aimed at a way silent data goes wrong:

1. **Unknown keys are errors.** `extra="forbid"` throughout, so `dificulty:`
   fails rather than taking a default.
2. **Every `assert:` name must exist in the check registry.** A typo is a build
   failure with a suggestion attached, not a check that never runs.
3. **Domain value objects are constructed inside the validators.** The schema
   restates no rule the domain already holds; it calls `ExerciseId`, and
   `InvalidValueError` subclasses `ValueError` so Pydantic attaches the field
   path.
4. **Structural correctness holes are refused outright.** At least one
   `required` check per scenario, no counter-example naming a check id that does
   not exist, and every command in every reference list legal under the
   exercise's own `allowed_commands`.

Rules about a *good* exercise rather than a *representable* one — hints and
notes are non-empty, every required check carries an explanation — live in the
content test suite rather than in the schema. The domain should not refuse to
model an exercise someone is halfway through drafting.

`practice validate` runs the same code in CI and at the command line, reports
every problem in every file in one pass, located to the field, and exits
non-zero.

## Consequences

- **Adding an exercise is writing files.** No Python, no imports, no recompile.
  The seventy-first exercise costs what the second one did, which is the only
  version of this project that reaches seventy.
- **Content is reviewable by reading it.** A YAML diff shows what the exercise
  asserts; a Python diff shows how it is implemented. For an artefact whose job
  is to teach, the first is the useful review.
- **The registry makes the assertion vocabulary a closed set**, which is what
  turns "the exercise silently lost a check" into a build failure. It also makes
  the vocabulary's growth visible: every new assertion is a deliberate addition
  to one file.
- **Cost: the schema is a second place the shape of an exercise is written
  down.** Mitigated by constructing domain objects inside the validators rather
  than restating their rules — but the field list itself genuinely exists twice,
  and adding a field means touching both. Accepted, because the alternative is a
  schema that validates less than the domain requires.
- **Cost: strictness is friction while drafting.** `extra="forbid"` means a
  half-written file fails rather than loading with defaults. This is the right
  trade for a library that ships, and the wrong one for a scratchpad; the answer
  is to draft in a scratch directory, not to loosen the schema.
- **Cost: YAML.** Significant whitespace, `no` parsing as `False`, and multiline
  string modes that are genuinely confusing (`|`, `|-`, `>`). It is still the
  right choice for content a human writes and reads, for the reason below.
- **Risk this introduces: data drifting from the engine.** A check spec can name
  parameters the Phase 5 function does not read, and Phase 2 cannot catch it —
  only the name is validated, not the parameter contract. Mitigated when the
  check functions land, by extending the registry from a set of names to a
  mapping of names to parameter contracts.

## Alternatives considered

- **Exercises as Python modules**, each a class or a registered function. The
  strongest argument for it is that everything is then checked by mypy,
  including the parameters of every assertion — which is exactly the hole named
  above. Rejected on the marginal cost of an exercise, which is the deciding
  constraint. It also makes content authoring a programming task, which
  narrows who can do it to people who are in a programming mood, and that
  includes the author on a Tuesday evening.
- **A hybrid: data for metadata, Python for checks.** Tempting, and the worst of
  both — the interesting part of an exercise (what it asserts, and why) ends up
  in the half that costs the most to write.
- **TOML instead of YAML.** Genuinely better specified, and the standard Python
  answer since 3.11 ships `tomllib`. Rejected on multiline strings: an exercise
  is mostly prose — a prompt, four hints, an explanation per check — and TOML's
  triple-quoted strings inside an array of tables is a markedly worse reading
  experience than YAML's `|` blocks. The format optimises for the wrong thing
  here.
- **JSON.** No comments and no multiline strings. Not a serious candidate for
  hand-authored content, and worth writing down only because it is the default
  answer to "what format" and the reason it loses is specific.
- **A database, with an authoring UI.** Solves nothing that matters and loses
  the thing that matters most: content in git, diffable, reviewable in a pull
  request, and recoverable. Also an authoring UI is a second product.
- **No schema — just load the YAML and trust it.** The cheapest option, and the
  one that turns every content bug into a runtime surprise during an attempt.
  The specific failure it permits is an exercise that grades with one fewer
  check than its author wrote and reports success, which is the failure ADR 0003
  already committed to designing against.

## Revisit if

Authoring an exercise routinely requires an escape hatch — a `python:` key, a
custom check written in code, a field that only one exercise uses. A handful of
new assertion types is normal vocabulary growth. Needing to run arbitrary code
to express an exercise means the declarative model has failed and this decision
reopens, along with ADR 0003's.

Also revisit if the schema and the domain start disagreeing in practice rather
than in theory: two or three bugs traceable to a field validated in one place
and not the other would mean the "construct domain objects inside validators"
discipline is not holding on its own.

## Validated in Phase 2 — 2026-09-30

Three exercises load, validate, and round-trip to domain aggregates:
[`git/revert-a-pushed-commit`](../../content/git/revert-a-pushed-commit/),
[`git/recover-a-lost-commit`](../../content/git/recover-a-lost-commit/) and
[`katas/two-sum`](../../content/katas/two-sum/). `practice validate` passes on
all three and reports a deliberately broken file with every problem located to
the field.

Two of the four strictness rules earned their place immediately. Building domain
objects inside validators surfaced "a scenario needs at least one required
check" as an error located at `scenario`, with no rule restated — and, less
expectedly, showed that a Pydantic constraint *duplicating* a domain invariant
makes errors worse rather than merely redundant: `min_length=1` on `checks`
alongside the domain's own rule turned one mistyped assertion into two errors,
the second of which sent the reader looking for a bug that was not there. The
registry check caught its first typo in a test fixture within the hour.
