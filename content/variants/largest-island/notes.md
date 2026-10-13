# The flood already knew the answer

Revealed after grading. This is "Max Area of Island" (LeetCode 695).

Counting islands runs a flood from each unvisited land cell and adds one. This
version runs exactly the same floods and asks each one how far it got. The
change is three lines, and one of them exposes a bug the original could hide.

```python
grid[top][left] = 0
stack = [(top, left)]
area = 0
while stack:
    y, x = stack.pop()
    area += 1
    for ny, nx in neighbours(y, x):
        if grid[ny][nx] == 1:
            grid[ny][nx] = 0          # marked on the way in
            stack.append((ny, nx))
```

## Mark on push, not on pop

If a cell is only marked visited when it is popped, two of its neighbours can
each push it before either copy comes off the stack. Counting islands does not
care: the cell is processed twice, finds nothing new the second time, and the
island is still one island. Counting *cells* cares very much — a 3x3 block
comes out larger than nine.

So the same flood was always slightly wrong, and the old question could not
see it. That is the general lesson of a follow-up that asks for more detail
than the original: it is an audit of the code you already wrote.

## What the twist was testing

Whether you can change what a traversal *returns* without rewriting it. The
other answers to this that come up — the perimeter of an island, the number of
distinct shapes, whether an island touches the edge — are all the same flood
with a different thing accumulated, and the skill is seeing the traversal and
the bookkeeping as two separate parts.
