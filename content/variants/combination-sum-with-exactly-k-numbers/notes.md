# Two counters, one answer condition

Revealed after grading. LeetCode's "Combination Sum III" (216) is the
each-number-once cousin of this.

The standard search carries one number down the recursion — what is left of
the target — and a combination is complete when it hits zero. This version
carries two, and the only real question is how they combine:

```python
if left == 0:
    if remaining == 0:
        results.append(tuple(chosen))
    return
```

Both must run out together. `remaining == 0` with numbers still to choose is
the shorter combination the limit exists to exclude; `left == 0` with target
remaining is simply a wrong sum. Check either one alone and you have solved
"at most" or "any sum".

## The second counter makes pruning better

In the standard search, a branch dies when a candidate exceeds what remains.
Here you know more: `left` further numbers are coming, and because
combinations are built in ascending order, each is at least the current
candidate. So the smallest total still to be added is `left * candidate`, and

```python
if candidate * left > remaining:
    break
```

cuts far earlier than `candidate > remaining` does. There is a matching bound
from above — `left * largest < remaining` cannot be rescued — which the
reference leaves out because the first one is already enough here.

A constraint that looks like extra work is usually extra information, and
extra information is what pruning is made of.

## What the twist was testing

The base case. The standard one returns as soon as the target is met, and it
is easy to leave that line where it is and add a length check after it — at
which point `(4,)` is returned for a `count` of 2, or the search stops before
it has looked for longer combinations at all.
