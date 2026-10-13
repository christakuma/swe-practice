# XOR turns two numbers into one question

Revealed after grading. This is "Hamming Distance" (LeetCode 461).

There is nothing new to learn about counting bits here. The whole exercise is
the step before it:

```python
differing = a ^ b
```

Exclusive-or is 1 where its inputs disagree and 0 where they agree, so
`a ^ b` *is* the set of positions being asked about. Count its set bits with
the loop you already have.

The mistakes are all substitutions for that one operator. `a | b` counts
positions where either has a 1, including the ones they share. `a & b` counts
only the shared ones. Adding the two separate bit counts gives the right
answer exactly when the numbers have no 1s in common.

The habit worth keeping: when a problem compares two things bit by bit, ask
what single value would describe the comparison. For "differ", it is XOR; for
"both set", AND; for "set in the first and not the second", `a & ~b`.
