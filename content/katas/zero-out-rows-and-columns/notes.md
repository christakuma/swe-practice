# Zero Out Rows and Columns — store the notes inside the data

Revealed after grading. The problem is the classic one (LeetCode 73); the
wording above is ours. It is the best short example of a specific move: when
you need `O(m + n)` bookkeeping and are allowed `O(1)` space, look for
somewhere inside the input that is already the right shape.

## Why you cannot clear as you scan

```python
for r in range(rows):
    for c in range(columns):
        if matrix[r][c] == 0:
            clear_row(r); clear_column(c)    # wrong
```

The zeros you write are indistinguishable from the zeros you are looking for,
so clearing cascades and the whole matrix goes to zero. Any correct solution
must separate **record** from **write**. The only question is where the record
lives.

## The honest intermediate answer

```python
zero_rows = {r for r, row in enumerate(matrix) if 0 in row}
zero_columns = {c for c in range(columns) if any(row[c] == 0 for row in matrix)}
for r in range(rows):
    for c in range(columns):
        if r in zero_rows or c in zero_columns:
            matrix[r][c] = 0
```

Correct, readable, `O(m·n)` time, `O(m + n)` space. **Write this first.** It is
the version to ship if nobody has specified a space bound, and it is the one to
reach for in review. Everything below buys a constant factor of memory at a
real cost in clarity.

## The move to O(1)

What the sets hold is **one flag per row and one flag per column**. The matrix
already contains a strip of exactly that shape: its own first row and first
column. Use them as the notebook.

```python
clear_first_column = False
for r in range(rows):
    if matrix[r][0] == 0:
        clear_first_column = True
    for c in range(1, columns):
        if matrix[r][c] == 0:
            matrix[r][0] = 0
            matrix[0][c] = 0
```

Then write the interior from the markers, and clear the marker strip last.

## The two details that make it work

**`(0, 0)` would have to mean two things.** It is both "row 0 contains a zero"
and "column 0 contains a zero", and one cell cannot hold two independent bits.
So column 0 gets an ordinary boolean of its own and `(0, 0)` is left to speak
only for row zero. That single scalar is the entire `O(1)` overhead — and
noticing the collision is most of the problem.

**Order is load-bearing, twice over.** The interior must be written *before*
the marker strip is cleared, because zeroing a marker destroys what it was
recording. And the interior scan must start at `(1, 1)`: include the marker
strip in the read and you are treating notes as data, which re-triggers on them
and cascades exactly like the naive version.

Clearing row zero before column zero matters for the same reason — row zero's
decision depends on `matrix[0][0]`, which clearing column zero would overwrite.
Hence the comment in the reference: *only now, and only in this order*.

## Is it worth it?

Honestly: usually not. The set version is two lines, obviously correct, and
`O(m + n)` space on an `O(m·n)` input is a rounding error — for a 1000×1000
matrix that is 2000 integers against a million. The marker version earns its
place when the matrix is enormous relative to available memory, which is rare,
and loses on every axis a reviewer cares about.

The reason to be able to write it anyway is that **the technique generalises
and the problem does not.** Encoding auxiliary state inside the data structure
you were given is how in-place linked-list reversal avoids a stack, how cycle
detection with pointer-marking works, how counting sort reuses its output
buffer, and how the index-as-hash trick solves "find the duplicate" in `O(1)`
space. This kata is the cheapest place to learn it.

## On the tests

`test_agrees_with_a_reference_on_every_small_zero_one_matrix` enumerates **all
2^(m·n) arrangements** up to 3×4 against the set-based version. That is the
test doing the work, and the reason is that marker schemes fail on specific
*configurations* rather than at specific sizes: a zero in row zero but not
column zero, a zero at the origin, a zero in column zero only. Picking those
cases by hand means first knowing which ones matter — enumerating all 4096 of
them does not.

When the input space is small enough to enumerate, enumerate it. Exhaustive
beats clever at finding the case you did not think of.

## What to take away

**`O(1)` space usually means "find existing storage", not "need less
information".** The information requirement here is fixed at one bit per row
and column; the only thing the clever version changes is where those bits sit.
Asking "is there already somewhere in the input shaped like what I need?" is
the move — and asking "is the constant factor worth the loss of obviousness?"
is the judgement that should follow it.
