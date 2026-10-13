# Find out first, paint afterwards

Revealed after grading. This is "Coloring A Border" (LeetCode 1034).

The paint bucket can recolour as it walks, and usually does: a painted pixel
no longer matches the original colour, so the repaint doubles as the visited
mark. That economy is the first thing this version takes away.

A border pixel is defined by its neighbours — *is that one in the region?* —
and "in the region" has been spelled "is the original colour". Paint a border
pixel and its neighbour, looking back at it, sees a different colour and
concludes it is touching the outside. Interior pixels next to an
already-painted border pixel get painted too, and the border creeps inward
until the whole region is recoloured.

So the three steps stay apart:

1. **Collect** the region as a set of coordinates. Change nothing.
2. **Select** the pixels with a neighbour off the image or outside the set.
3. **Paint** those.

```python
border = [
    (r, c) for r, c in region
    if not {(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)} <= region
]
```

An off-image neighbour is never in the set, so the one test covers "on the
edge of the image" as well.

## The cases that find the shortcuts

- **New colour equals old colour.** Nothing should change. A walk that uses
  repainting as its visited mark never terminates.
- **New colour equals a neighbouring region's colour.** A walk that tests
  colours after painting can leak into the neighbour, or misjudge the border.
- **A hole.** The pixels round a hole are border pixels although they are
  nowhere near the outside of the region.

## What the twist was testing

That reading and writing the same structure in one pass is only safe when
what you write cannot change what you later read. In the plain fill that
happens to be true. Here it is not, and the general remedy is the one in
`zero-out-rows-and-columns`: decide everything from the original, then write.
