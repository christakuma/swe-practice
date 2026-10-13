# The answer was on the stack the whole time

Revealed after grading.

Detecting a cycle with a depth-first search means noticing a dependency that
is **still in progress** — a name on the path from the start to where you are
now. The standard solution returns `True` at that moment. But look at what it
is holding when it does: the path itself, and the cycle is on it.

```
path:      start -> middle -> x -> y
                              ^    |
                              +----+      y depends on x, already on the path
```

Not all of the path, though. `start` and `middle` are how the search *reached*
the cycle. The cycle is the path from the repeated name onwards:

```python
if following in position:
    return path[position[following]:]
```

`position` maps each name on the path to its index, so the slice is one
lookup. Because the path was built by following dependencies, the names come
out in dependency order with nothing more to do.

## Three states, and why two are not enough

Each name is unvisited, **on the path**, or **done**. Only meeting a name on
the path is a cycle. A diamond — `a` needs `b` and `c`, and both need `d` —
reaches `d` twice, and the second time `d` is done. One `visited` set cannot
tell those apart and reports a cycle through `d` that does not exist. Here it
would also have to invent the names for it.

## What the twist was testing

That "yes" was understood as a compression of something. A build tool that
says *there is a circular dependency* and stops is useless; the one that
prints `x -> y -> x` has done the same search and simply not thrown the
evidence away. Returning a witness instead of a verdict is nearly always this
cheap, and nearly always what the caller actually wanted.
