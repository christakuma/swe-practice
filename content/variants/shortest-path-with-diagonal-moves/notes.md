# The same search over a bigger neighbourhood

Revealed after grading. This is "Shortest Path in Binary Matrix"
(LeetCode 1091), which has always had eight directions.

Breadth-first search finds the shortest route whenever every step costs the
same, and a diagonal step here costs the same as a straight one. So the
algorithm is untouched and only the offsets change.

Two things the wider neighbourhood changes about the *answers*: an open
`n x n` grid now takes `n` cells rather than `2n - 1`, and two walls that meet
at a corner no longer block the gap between them. That second one is the
case to ask about in an interview — some versions forbid squeezing through.
