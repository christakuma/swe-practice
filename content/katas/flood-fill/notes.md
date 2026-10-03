# The whole kata is one guard

```python
if original == colour:
    return image
```

Without it, filling a region with the colour it already has never terminates.
The reason is worth tracing, because it is a class of bug rather than a special
case:

1. the walk uses **painting as its visited marker** — a pixel that has been
   recoloured no longer matches `original`, so it is not pushed again
2. painting a pixel its own colour changes nothing
3. so no pixel is ever marked visited
4. so two adjacent pixels push each other for ever

The input that triggers it looks like a no-op — "fill this red region with red"
— which is exactly the kind of input nobody thinks to test. And a `visited` set
instead of painting would not have the bug at all, at the cost of O(n) space.

That is the general shape: **when a mutation doubles as a marker, check that the
mutation is actually a change.**

## Capture before you paint

```python
original = image[row][column]     # before any painting
```

Obvious once stated and easy to get wrong when the first paint happens before
the loop. The moment the starting pixel is recoloured, the colour you were
matching against no longer exists anywhere you can read it.

## Same walk, different bookkeeping

[count-islands](../count-islands/notes.md) walks for the same reason and counts
components; this one paints. Same four-neighbour expansion, same explicit stack
for the same reason — a 300×300 single-colour image is ninety thousand connected
pixels and Python recurses a thousand deep.

What differs is only what happens at each visited cell:

| kata | at each cell |
|---|---|
| count islands | nothing; the count is per fresh walk |
| flood fill | paint it |
| [shortest path](../shortest-path-in-a-grid/notes.md) | record its distance — and use a **queue** |

The third one is the one that is not interchangeable: for distances the order of
visiting is load-bearing.

## Why "started with the same colour" is in the specification

Compare the region to the *original* colour, not to the colour of the pixel you
came from. The two differ as soon as painting begins, and comparing against the
neighbour you arrived from would let the fill escape into a neighbouring region
that happens to be the new colour. The suite's "separate region of the same
colour" test is the other side of this: the fill must spread by **connectivity**
and not by matching colour globally.
