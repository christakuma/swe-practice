# Rotate a Matrix in Place — factor the transform

Revealed after grading. The problem is the classic one (LeetCode 48); the
wording above is ours. It is a good exercise in *not* solving the problem you
were given.

## Why the direct attack is unpleasant

An element at `(r, c)` has to end up at `(c, n-1-r)`. Writing it there
overwrites whatever lived at that position, so you cannot loop over the grid
assigning — you have to rotate four elements at a time around a cycle, ring by
ring, with a temporary:

```python
for layer in range(n // 2):
    last = n - 1 - layer
    for i in range(layer, last):
        offset = i - layer
        top = matrix[layer][i]
        matrix[layer][i] = matrix[last - offset][layer]
        matrix[last - offset][layer] = matrix[last][last - offset]
        matrix[last][last - offset] = matrix[i][last]
        matrix[i][last] = top
```

Correct, `O(n²)`, `O(1)` space. It is also five index expressions that are each
individually easy to get wrong, and nothing about it tells you whether it is
right other than running it.

## The move

Factor the rotation into two operations that are each trivially correct:

```python
for i in range(n):                       # transpose
    for j in range(i + 1, n):
        matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
for row in matrix:                       # then reverse each row
    row.reverse()
```

**Transpose** is a reflection across the main diagonal. **Reversing each row**
is a reflection across the vertical centre line. Two reflections compose to a
rotation, and these two compose to a clockwise quarter turn.

Track one element to convince yourself: `(0,0)` is fixed by the transpose, then
the row reversal sends it to `(0, n-1)` — the top-right, which is exactly where
a clockwise turn puts the top-left.

Same `O(n²)` time, same `O(1)` space, and both halves are operations you can
verify by inspection.

**The transferable idea: when a transformation is awkward to write directly,
look for simpler transformations whose composition it is.** Anticlockwise is
the same two steps in the other order (reverse rows, then transpose), 180° is
reverse the row order and reverse each row, and a vertical flip is just
`matrix.reverse()`. One decomposition gives you the whole family.

## The bug that looks like nothing happened

```python
for j in range(n):        # instead of range(i + 1, n)
```

A transpose has to swap each pair **once**. Running `j` over the full row swaps
every pair twice — `(i,j)` with `(j,i)` and later `(j,i)` with `(i,j)` — so the
transpose is a no-op and the whole function reduces to reversing each row.

What makes it nasty is the failure mode: the matrix comes back looking
untouched rather than wrongly rotated, which reads like the function was never
called. `test_actually_changes_the_matrix` exists to name it as a rotation bug
instead of letting it present as a harness problem.

## In place means the caller's object

```python
matrix = [list(row) for row in zip(*matrix[::-1])]    # does nothing
```

Rebinding the local name leaves the caller holding the original grid. Nothing
is returned, so this function silently has no effect — and it passes any test
that inspects a value the function returns, because there isn't one.

`test_mutates_the_grid_the_caller_holds` goes further and checks the **row
lists are the same objects**. `matrix[:] = [list(r) for r in ...]` mutates the
outer list but replaces every row, which allocates the second grid the problem
forbids. `row.reverse()` mutates in place; `row[::-1]` builds a copy.

## The property test

`test_four_rotations_return_the_original` is the test to copy into your own
work. Four quarter turns is the identity, which holds for *any* square matrix
and needs no expected-value table to state. A rotation that is internally
self-consistent but is not actually a quarter turn — a transpose alone, a
reflection, an anticlockwise turn — fails to close the loop.

Properties like that are usually cheaper to write than examples and cover more:
involutions (`reverse_bits` twice), round-trips (encode then decode), and
identities (four rotations) are all available for free once you notice the
structure.

## What to take away

Two reflections make a rotation. More usefully: **a hard index-juggling problem
often has a factorisation into easy ones**, and the factored version is not
just easier to write — it is easier to *believe*, which matters more when you
come back to it.
