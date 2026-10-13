# From "any clash?" to "how many at once?"

Revealed after grading. The bridge between "Meeting Rooms" and "Meeting Rooms
II" (LeetCode 252 and 253).

One person can attend everything if no two meetings overlap, and after a sort
that is a check on neighbours. Two people can cover everything if no *three*
overlap — and three meetings can all overlap without being neighbours in any
useful sense, so the neighbour check does not generalise.

What generalises is the count. Sort starts and ends separately, walk the
starts, and release every end at or before each one:

```python
if begun - released > people:
    return False
```

The standard problem is this with `people = 1`. That is worth noticing in the
other direction too: a yes-or-no question is often a threshold on a number,
and the number is usually the more useful thing to know how to compute.
