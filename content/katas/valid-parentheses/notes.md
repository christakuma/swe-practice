# Counting cannot see order

The first idea is to count: as many `(` as `)`, as many `[` as `]`. It rejects
`"(("` correctly and accepts `"([)]"`, which has exactly one of each and is not
valid. Nesting is a statement about *order*, and a count has thrown the order
away before you look at it.

The second idea — a single depth counter, incremented on openers and decremented
on closers, failing if it ever goes negative — is genuinely correct for **one**
kind of bracket, and that is worth knowing because it is O(1) space. It breaks
the moment there are two kinds, for the same reason: a counter cannot remember
*which* bracket is open.

## What the problem actually asks for

Each opener is a promise to close. Each closer must redeem the **most recent**
outstanding promise, because nesting means a group closes before the one that
contains it. "Most recent outstanding" is a stack, and once you see that, the
code is five lines.

```
"{[()]}"      stack
 {            [ { ]
 [            [ {, [ ]
 (            [ {, [, ( ]
 )            [ {, [ ]        ( matches, pop
 ]            [ { ]           [ matches, pop
 }            [ ]             { matches, pop
              empty -> valid
```

## The two failure modes

Both are required and the second is the one people leave out:

1. **A closer that does not match.** Either the stack is empty — a closer with
   nothing open, `")("` — or the top is the wrong kind, `"(]"`.
2. **A non-empty stack at the end.** Promises never kept: `"(("`. A solution
   that returns `True` by default after the loop accepts every unclosed string,
   and passes every test that has a mismatch in it.

The suite tests them separately for that reason. They are not two phrasings of
one check.

## Where this generalises

A stack is the data structure for anything with nesting, and the family is
bigger than it looks:

- matching brackets, HTML tags, `begin`/`end` blocks
- evaluating or converting expressions (shunting-yard, reverse Polish)
- depth-first traversal — the call stack *is* the stack, which is why DFS is
  usually written recursively and iteratively with an explicit stack
- undo history, and the "most recent outstanding thing" shape generally

The giveaway in a problem statement is a constraint that refers to the most
recent unfinished item.

## Complexity

O(n) time: each character is pushed at most once and popped at most once. O(n)
space in the worst case — `"((((..."` pushes everything before popping anything
— and that is unavoidable for multiple bracket kinds, because the stack *is* the
record of what is open.
