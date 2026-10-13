# Decide after you have seen the whole island

Revealed after grading. This is "Number of Closed Islands" (LeetCode 1254),
with land and water the usual way round.

The standard count makes its decision at the first cell: found land, add one,
sink the island. This version cannot. Whether an island counts depends on
cells you have not looked at yet.

## Two ways to order the work

**Sink the edge first.** Run a fill from every land cell on the border. That
removes every disqualified island completely. What remains is all enclosed,
so count it the standard way. Two passes, no flags, and the reference does
this.

**Decide per island.** Fill each island, and carry a flag that turns false if
any cell is on the border. Count the island when the fill finishes with the
flag still true.

## The trap in the second way

```python
def enclosed(row, column):
    if on_edge(row, column):
        return False          # stops here
    ...
```

Returning as soon as an edge cell appears leaves the rest of the island
unvisited. The outer scan finds those cells later, sees land in the interior,
and may count a piece of an island it has already rejected. The fill has two
jobs — answering the question and marking cells as seen — and the early
return does the first and abandons the second.

The recursive form of the same bug is `return fill(a) and fill(b)`: `and`
short-circuits, so the second fill never runs. Evaluate both, then combine.

## What the twist was testing

That a property of a *group* is not a property of the cell you met it by. The
same shift shows up in "largest island" — nothing can be said until the fill
is finished — and here it bites harder, because the wrong answer is not
merely early but depends on which corner of the island the scan reached
first.
