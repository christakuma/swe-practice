# Push positions, and keep a floor

Revealed after grading. With one kind of bracket this is "Longest Valid
Parentheses" (LeetCode 32).

The standard checker pushes openers and pops them, and the only thing it
ever asks of the stack is "empty or not?". To measure a stretch you need to
know *where* things are, so the stack holds **positions**.

## The idea

Every balanced stretch sits strictly between two neighbouring unmatched
characters. If you knew the positions of all the unmatched characters, the
answer would be the biggest gap between consecutive ones.

The stack finds that as it goes. Its bottom entry is a **floor**: the last
position that can never be matched (`-1` to begin with). Above the floor are
openers still hoping.

```python
if character not in PARTNER:
    stack.append(position)
elif len(stack) > 1 and text[stack[-1]] == PARTNER[character]:
    stack.pop()
    longest = max(longest, position - stack[-1])
else:
    stack = [position]
```

After a successful pop, `stack[-1]` is the nearest unmatched position to the
left, so `position - stack[-1]` is the length of the balanced stretch ending
here. In `"()()"`, both pairs are measured from the same `-1`, which is why
they join into 4 with no code for joining.

## What three kinds of bracket add

With only `(` and `)`, a closer fails in one way: nothing to pop. Then it
becomes the new floor.

With three kinds it can also fail by finding the **wrong opener** on top. In
`"(()]()"`, the `]` meets a `(`. That `]` will never be matched — and so
neither will anything still on the stack, because closing it would mean
reaching across the `]`. The `]` is the new floor. Replacing the stack with
it is the tidy way to say so; pushing it on top of the dead openers works
equally well, since nothing can match past it.

What does not work is treating the mismatch as a match — popping the wrong
opener and carrying on — or testing only whether the stack is empty. Those
are the bugs the three-bracket version exists to catch.

## What the twist was testing

That a stack can carry more than the thing being matched. Positions instead
of characters turns a yes/no checker into a ruler — the same upgrade that
turns "is there a next greater element" into "how far away is it".
