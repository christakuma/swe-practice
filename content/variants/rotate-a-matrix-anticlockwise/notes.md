# The same two moves, the other mirror

Revealed after grading. The follow-up to "Rotate Image" (LeetCode 48) that
checks whether the two-step trick was understood or memorised.

A quarter turn is a transpose followed by a mirror:

- transpose, then reverse **each row** → clockwise
- transpose, then reverse **the order of the rows** → anticlockwise

Nobody remembers which is which, and nobody needs to. Take
`[[1, 2], [3, 4]]`, apply the two moves on paper, and see where the 2 ends up.
Anticlockwise sends the top-right corner to the top-left.

`matrix.reverse()` reverses the outer list in place, which is the cheap half:
the rows themselves are not copied, only reordered.
