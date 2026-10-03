# The window only ever moves forward

The naive solution is two nested loops: from each start position, extend until
you hit a character you have already seen. That is O(n²) and it recomputes
something it already knew — when the window starting at index 3 fails because of
a duplicate, the window starting at index 4 is going to re-examine almost
exactly the same characters.

The insight is that **the end of the window never moves backwards**, and neither
does the start. Both only ever advance, so each one traverses the string once and
the whole thing is linear:

```
abba
^^       start=0 end=1   valid, longest=2
^^^      start=0 end=2   'b' repeats
  ^^     start=2 end=2   jump past the previous 'b'
  ^^^    start=2 end=3   valid, longest=2
```

## The part that is easy to get wrong

```python
start = max(start, last_seen[character] + 1)
```

Without the `max`, `abba` returns 3. Here is why: at the final `a` (index 3),
`last_seen['a']` is 0 — an occurrence from *before* the current window began.
Jumping unconditionally sets `start = 1`, which moves the window backwards over
a `b` that is already inside it, and the window is no longer valid at all.

The dict remembers every character ever seen, not just the ones in the window.
So an entry can be stale, and `max` is what says "a duplicate behind the window
is not a duplicate".

The alternative design avoids the problem by construction: keep a `set` of the
characters currently *in* the window, and when you hit a duplicate, remove
characters from the left one at a time until it is gone.

```python
window: set[str] = set()
start = 0
for index, character in enumerate(text):
    while character in window:
        window.remove(text[start])
        start += 1
    window.add(character)
```

That is also O(n) — the `while` loop advances `start`, which happens at most n
times in total across the whole run — and it has no stale state to reason about.
It does more work per step and is harder to get wrong. Both are worth being able
to write; the index version is the one that generalises to "at most k repeats".

## Recognising the shape

Sliding window applies when the thing you are looking for is **contiguous** and
the property you are checking is **monotone**: if a window is invalid, every
larger window containing it is also invalid. That is what lets the start move
forward and never come back.

- longest substring with no repeats → this kata
- smallest window containing all of a set of characters
- longest subarray with sum at most k, for non-negative values
- maximum sum of any k consecutive elements

And the counter-case worth knowing: *longest subarray with sum at most k* when
values can be negative is **not** a sliding-window problem, because adding an
element can make a sum smaller. The monotonicity is doing the work, not the
window.

## Complexity

Time O(n): every index is visited once as the end, and `start` advances
monotonically. Space O(k) where k is the number of distinct characters — bounded
by the alphabet, so O(1) if you are willing to call Unicode a constant, which is
the kind of claim worth stating rather than assuming.
