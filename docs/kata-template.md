# Authoring a kata

A kata is a directory under `content/katas/<slug>/` (or `content/variants/<slug>/`
for a variant, [ADR 0028](adr/0028-a-variant-is-a-whole-exercise-offered-under-its-base.md)):

```
exercise.yaml   the statement, the signature, the examples
stub.py         what the solver starts from
solution.py     the reference answer
tests.py        the hidden suite
notes.md        why this is worth practising
```

`exercise.yaml` is the only file with a schema. The skeleton below is every key a
kata can have; `practice validate` rejects one that is wrong and says where.
The reasoning for the `signature:` block is
[ADR 0035](adr/0035-a-kata-declares-its-signature-and-its-bounds-are-enforced.md).

```yaml
schema_version: 1
id: katas/contains-a-duplicate        # <track>/<slug>; variants/<slug> for a variant
kind: kata
title: Contains a Duplicate
difficulty: easy                      # easy | medium | hard
tags: [arrays, hash-sets]             # a variant's tags must be tags a listed kata has
estimated_minutes: 10

prompt: |
  The story and the rules. It does NOT need to restate the argument names and
  types: the page draws an Input / Output header from `signature:` above the
  constraints, the same way for every kata.

hints:
  - "A nudge, not the answer."

kata:
  language: python
  stub: stub.py
  tests: tests.py
  reference: solution.py
  time_limit_seconds: 10
  complexity:
    expected_time: "O(n)"
    expected_space: "O(n)"

  signature:
    functions:                        # module-level functions the tests import
      - name: has_duplicate
        summary: Return whether any value appears more than once.
        parameters:
          - name: numbers
            type: list[int]           # printed as written; the stub must annotate the same
            description: the values to check. May be empty, and may be long.
            length: {min: 0, max: 10**6}            # len(numbers)
            values: {min: -10**9, max: 10**9}       # every integer inside it
        returns:
          type: bool
          description: True if some value occurs at least twice, False otherwise.
    # classes:                        # and/or classes the tests construct
    #   - name: WordStore
    #     summary: A word store.
    #     methods:
    #       - name: __init__
    #         summary: Create an empty store.
    #       - name: add
    #         summary: Store a word.
    #         parameters: [...]
    #         returns:
    #           type: None            # the only type that needs no description

  notes:                              # what a range cannot say. Printed, never checked.
    - All values are distinct.

  examples:                           # run against solution.py by the content suite
    - input: |
        has_duplicate([1, 2, 3, 1])
      output: |
        True
      explanation: |
        1 appears twice.
```

## The four bounds

A parameter may declare any of these, each `{min, max}` with either end optional.
An end is an integer or integer arithmetic, and **is printed as you spell it**:
write `2 * 10**5`, not `200000`.

| Key | Bounds | Renders as |
|---|---|---|
| `length` | `len(param)` | `0 <= len(numbers) <= 10**6` |
| `item_length` | the length of each element | `0 <= len(words[i]) <= 20` |
| `values` | every integer inside it, however nested; `node.value` for nodes | `-10**9 <= numbers[i] <= 10**9` |
| `nodes` | how many nodes are reachable from it | `0 <= the number of nodes in root <= 500` |

The reference solution runs with a footer that raises if the hidden suite passes
anything outside them, so **a bound must be at least as wide as the largest thing
`tests.py` passes**. If the suite passes `10**5 + 1` characters on purpose, say so:
`max: 10**5 + 1`.

Leave a parameter unbounded rather than declare a bound you have not measured.
And do not declare `values` or `nodes` on a parameter whose tests instrument it
(a node that raises when touched, an allocation count): the probe would trip the
instrument. Put it in `notes:`.

## The stub's docstrings are generated

After editing `signature:` run

```bash
uv run python tools/migrate_katas.py --stubs <slug>
```

which rewrites each declared callable's docstring (summary, `details`, `Args:`,
`Returns:`, `Raises:`) in `stub.py`. `test_its_stub_docstrings_are_generated_from_the_signature`
compares them byte for byte, and `test_its_stub_and_reference_agree_with_the_declared_signature`
checks names, parameter order and, for the stub, every annotation.

## Before you commit

```bash
uv run practice validate
uv run pytest -q --no-cov -m content -k <slug>      # about four seconds
```
