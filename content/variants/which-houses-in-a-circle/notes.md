# The table was the answer all along

Revealed after grading. "House Robber II" (LeetCode 213), asked for the
houses rather than the haul.

The total needs two numbers:

```python
previous, current = current, max(current, previous + amount)
```

and that loop cannot tell you which houses it chose, because by the end it
has forgotten every decision but the last. To recover the selection you keep
the whole table — `best[i]` is the most from the first `i` houses — and read
it backwards:

```python
i = length
while i >= 1:
    if best[i] == best[i - 1]:
        i -= 1                      # house i - 1 added nothing: skip it
    else:
        picks.append(start + i - 1) # it was taken...
        i -= 2                      # ...so its neighbour was not
```

Nothing new was computed. The decisions were always in the table, as the
places where it goes up.

## Why backwards

Forwards, you cannot tell whether to take a house without knowing what comes
after it. Backwards, `best[i]` already accounts for everything before, so a
single comparison settles each house. This is the same reason every "print
the path" follow-up reads its table from the far end.

## The circle

Unchanged from the version that returns a total: solve the line without the
last house, solve the line without the first, keep the better. Two things to
watch now that positions matter:

- **The shift.** The second line starts at house 1. Its picks are positions
  in the line, and need `start +` to become positions in the circle.
- **One house.** Both lines are empty and both return nothing, but the right
  answer is to take it. It needs its own case, as it always did.

## Ties

`[4, 4, 4, 4]` has two best selections and the tests accept either. They
check what makes an answer right — in order, no two adjacent, adds up to the
best total — instead of comparing against one list. When you are asked for
"an" optimal solution, say out loud that there may be several, and ask
whether a particular one is wanted.

## What the twist was testing

Whether you know that a space optimisation is a trade. Rolling the table
down to two variables is the right thing when only the value is wanted and
exactly the wrong thing when the choices are. "Now tell me which" is the most
common follow-up to any optimisation problem, and the answer is nearly
always: keep the table, walk it backwards.
