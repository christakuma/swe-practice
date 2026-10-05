# Read a Matrix in Spiral Order — four numbers, and two guards

Revealed after grading. The problem is the classic one (LeetCode 54); the
wording above is ours. It is not conceptually hard, which is exactly why it is
instructive: the whole difficulty is in two `if` statements on the last ring,
and every square test case in the world will tell you your broken solution
works.

## The move

Hold four boundaries — the first and last rows still unread, the first and last
columns still unread. Each of four passes consumes a whole edge, then moves its
own boundary inward:

```python
top, bottom = 0, len(matrix) - 1
left, right = 0, len(matrix[0]) - 1

while top <= bottom and left <= right:
    for c in range(left, right + 1):        # top row, rightwards
        values.append(matrix[top][c])
    top += 1

    for r in range(top, bottom + 1):        # right column, downwards
        values.append(matrix[r][right])
    right -= 1

    if top <= bottom:                       # bottom row, leftwards
        for c in range(right, left - 1, -1):
            values.append(matrix[bottom][c])
        bottom -= 1

    if left <= right:                       # left column, upwards
        for r in range(bottom, top - 1, -1):
            values.append(matrix[r][left])
        left += 1
```

`O(m·n)` time — every cell consumed exactly once — and `O(1)` state beyond the
output. No grid of visited flags, which is the other common solution and costs
`O(m·n)` space to track something the boundaries already know.

## The two guards

This is the part worth remembering.

Once `top` and `bottom` have closed in on a **single remaining row**, the top
pass reads it left-to-right and then the bottom pass — whose row index is now
*that same row* — reads it right-to-left again. Every value in the final strip
comes out twice. Mirror image for a single remaining column and the left pass.

`if top <= bottom` and `if left <= right` are checked **after** the earlier two
passes have already moved their boundaries, so each one asks a live question —
"is there still a distinct row/column here?" — rather than a question about the
original shape. That ordering is why the guards cannot be hoisted to the top of
the loop body.

The reason this bug is worth a note of its own: **it cannot occur on a square
matrix.** An `n x n` spiral always closes on a single cell or a `2 x 2`, never
on a strip, so the unguarded version is perfectly correct on `3x3`, `4x4` and
`5x5` — the cases everybody tries first. `test_ends_on_a_single_middle_row`
uses `3x5` and `test_agrees_with_an_independent_spiral_at_every_small_shape`
sweeps all 81 shapes up to `8x8`, because varying *both* dimensions is the only
way to see it.

That generalises past this kata: **when a bug lives in a degenerate case, the
symmetric inputs you reach for first are the ones that hide it.** Sweep the
shape space, not just the size.

## The other good solution

Peel the top row, rotate what's left anticlockwise, repeat:

```python
values = []
while matrix:
    values.extend(matrix.pop(0))
    matrix = [list(row) for row in zip(*matrix)][::-1]
return values
```

Four lines, no boundaries, no guards, no off-by-ones — and genuinely a good
answer. It allocates a new grid on every turn, so it is `O(m·n)` extra space
and does more total work shuffling than reading. It also **consumes the
caller's matrix** unless you copy first, which `test_leaves_the_input_alone`
checks: destroying the input to produce a read-only answer is a real bug, not a
style preference.

It is used as the oracle in the test suite precisely because it shares no index
arithmetic with the four-boundary version. Two implementations that can only
agree by both being right is worth more than a table of expected values you
computed by hand — and the four-boundary one is the version to ship, because
the spiral is a *reading* operation and reading should not allocate.

## What to take away

The boundary-shrinking pattern is the reusable piece: **represent "the part not
yet processed" as a few indices rather than as a copied sub-structure.** It is
the same instinct as two pointers on an array, and it is what keeps the space
bound at `O(1)` here, in binary search, and in the in-place partition steps of
quicksort.

And when your loop has a special case on its final iteration, be suspicious of
test inputs that are too well-shaped to reach it.
