# A blocked cell is a zero

Revealed after grading. This is "Unique Paths II" (LeetCode 63).

The recurrence does not change — paths in from above plus paths in from the
left — and an obstacle needs no special machinery. Its count is zero, and a
zero adds nothing to the cells that would have been reached through it.

**The edges are where it goes wrong.** In the open grid the first row and
column are all 1, and code written for that case often initialises them that
way. With obstacles, a blocked cell on the top row makes every cell to its
right unreachable *along that row*. Let the same recurrence fill the edges
and the mistake cannot be made.

The closed-form binomial that solves the open grid is gone, incidentally.
Obstacles destroy the symmetry it depended on, and the table is the only
general answer.
