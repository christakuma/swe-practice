# One replacement fixes two counts

Revealed after grading. This is "Minimum Number of Steps to Make Two Strings
Anagram" (LeetCode 1347).

The yes-or-no version compares two tallies and asks whether they are equal.
This asks how far apart they are, and the only real question is what unit to
measure in.

Take `first = "bab"` and `second = "aba"`:

| | a | b |
|---|---|---|
| wanted | 1 | 2 |
| have | 2 | 1 |
| difference | +1 | −1 |

The second string has one `a` too many and one `b` too few. Those are not two
problems. Replacing the spare `a` with a `b` settles both, because a
replacement *moves* a unit from one count to another.

When the lengths are equal, total surplus equals total shortfall. So count
one side:

```python
surplus = Counter(second) - Counter(first)   # keeps positive differences only
return sum(surplus.values())
```

Summing the absolute differences counts each replacement at both ends and
gives exactly double.

## The answer that looks right

```python
sum(a != b for a, b in zip(first, second))
```

Counting the positions where the strings differ is the instinct, and it
answers a different question — how to make them *equal*. `"abcd"` and
`"dcba"` differ everywhere and are already anagrams. An anagram is a
statement about counts, and the moment position enters the solution it has
gone wrong.

## What the twist was testing

Turning a predicate into a distance. "Are these the same?" becomes "how many
steps apart?", and the step has to be defined with care: here one step
changes two counts by one each. Edit distance, Hamming distance and this are
all that same move applied to different notions of "same".
