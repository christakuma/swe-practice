# A character that falls short is a wall

Revealed after grading. "Longest Substring with At Least K Repeating
Characters" (LeetCode 395).

## Why the window does not work

"No repeats" has a property the sliding window depends on: if a window is
bad, every wider window containing it is bad too. So when it goes bad you
shrink, and you never need to look back.

"Every character at least `k` times" does not have it. `"ab"` fails for
`k = 2`; `"abab"` passes; `"ababc"` fails again. Growing can repair a window
and growing can break it. There is no rule for when to move the left edge.

## What to do instead

Count the whole string. Any character with fewer than `k` copies **cannot be
in the answer** — if the whole string does not have enough of it, no piece
does. So cut the string wherever it appears:

```
a a b c b a a          k = 2
      ^                c appears once: a wall
a a b   b a a
```

The answer is inside one of the pieces. Each piece is the same question
again, and has to be *recounted*: there are two b's in the whole string, but
one in each piece, so in each piece the b is now a wall.

```
a a b       ->   a a        qualifies: 2
```

A piece with no walls qualifies as it is.

## How deep it goes

Every cut removes at least one distinct character from the piece, so pieces
nest at most as deep as there are distinct characters. For lower-case text
that is 26, and the recursive version is fine.

The constraints here say any character. Start with `"aa"`; append a new
character and then the previous new character; repeat. Each level is cut by
its newest character into a piece that needs cutting again — one level per
character. Fifteen hundred characters is fifteen hundred nested calls, and
Python stops at a thousand.

The fix is the usual one: keep the pieces to examine on your own list.

```python
waiting = [text]
while waiting:
    piece = waiting.pop()
    ...
```

## The other standard answer

For a fixed alphabet there is a windowed solution after all: for each
`d = 1, 2, …, 26`, slide a window that holds *at most `d` distinct
characters* and check whether all of them reach `k`. Fixing the number of
distinct characters restores the monotonic property. It is `O(26 n)` and
worth knowing — and it depends on the alphabet being small, which this
version of the problem took away.

## What the twist was testing

Whether you check that a technique applies before using it. Flip "no
repeats" to "enough repeats" and the problem looks like the same window with
a different condition. It is not, and the reason — the condition is not
monotonic — is the thing to say out loud. Then: what *is* certain? A
character that falls short in the whole falls short everywhere.
