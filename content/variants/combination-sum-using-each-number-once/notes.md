# One copy of each value per position

Revealed after grading. This is "Combination Sum II" (LeetCode 40).

The standard problem lets a candidate be reused and promises the candidates
are distinct. This one withdraws both at once, and the two changes pull in
opposite directions: one is trivial and the other is the whole exercise.

## The trivial half

Recurse from `index + 1` instead of `index`. A candidate that has been chosen
is no longer on offer to the same combination.

## The half that matters

With repeats in the input, that alone returns duplicates. `[1, 1, 2]` with a
target of 3 produces `(1, 2)` twice — once starting from each 1.

The reflex is a `set`. It gives the right output and the wrong algorithm:
every duplicate is still *found* before it is discarded, and with thirty
equal candidates that is every subset of thirty things.

The fix is to not generate them:

```python
ordered = sorted(candidates)
...
for index in range(start, len(ordered)):
    if index > start and ordered[index] == ordered[index - 1]:
        continue
```

At one depth of the recursion, each distinct **value** is tried once. The
first copy of a value explores every combination that has that value in this
position; a second copy here would retrace exactly the same ground.

Note `index > start`, not `index > 0`. The skip applies to copies competing
for the *same* position. A second 1 is perfectly welcome one level down, as
the next element of a combination that already holds the first — that is how
`(1, 1, 6)` gets built.

## What the twist was testing

The difference between removing duplicates and not producing them. It is the
same lesson as three-sum's "skip equal neighbours", and it turns up in every
backtracking problem whose input can repeat: permutations, subsets,
partitions. Sort, then skip equal siblings.
