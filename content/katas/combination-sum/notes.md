# Combination Sum — prevent the duplicate, don't detect it

Revealed after grading. The problem is the classic one (LeetCode 39); the
wording above is ours. It is the library's second backtracking exercise after
[find a word in a grid](../find-a-word-in-a-grid/notes.md), and the thing worth
taking from it is how the *shape* of the recursion does a job that would
otherwise need explicit deduplication.

## The skeleton

Choose candidates one at a time, subtracting from the target. Zero remaining is
an answer; below zero is a dead end.

```python
def search(start, remaining):
    if remaining == 0:
        results.append(tuple(chosen))
        return
    for index in range(start, len(ordered)):
        candidate = ordered[index]
        if candidate > remaining:
            break
        chosen.append(candidate)
        search(index, remaining - candidate)     # index, not index + 1
        chosen.pop()
```

Choose, recurse, un-choose — the same three-step skeleton as the grid search,
with the snapshot taken on success because `chosen` keeps changing afterwards.

## The index rule is the whole kata

`search(index, ...)` rather than `search(index + 1, ...)` allows the **same**
candidate again, which is what "use as many times as you like" needs.

Starting from `start` rather than `0` is what makes these *combinations* rather
than *permutations*. It forbids ever going back to an earlier candidate, which
enforces non-decreasing order — so each multiset is constructed by **exactly
one path** through the search, and no deduplication is needed anywhere.

Three one-word variants, three different problems:

| recursive call | meaning |
|---|---|
| `search(0, ...)` | permutations — every ordering separately |
| `search(index, ...)` | combinations with repetition — this problem |
| `search(index + 1, ...)` | combinations without repetition — subsets |

Worth memorising as a set, because they are indistinguishable at a glance and
the failures are specific: `0` returns `(2,3,3)` and `(3,2,3)` as separate
answers; `index + 1` cannot build `(2,2,3)` at all.

## Prevent, don't detect

Compare with [three sum](../three-sum-to-zero/notes.md), where duplicate
triples had to be skipped explicitly in **three** places, each with its own
reasoning. Here the identical job is done by one word in one recursive call.

**That is the better kind of fix.** Same preference as generating only
palindromes in
[longest palindromic substring](../longest-palindromic-substring/notes.md)
instead of filtering candidates for the property: when you can structure the
search so the invalid cases are never constructed, you do not have to recognise
them — and you cannot forget a case.

When it is *not* available, explicit skipping is the honest fallback. The thing
to notice is which situation you are in: three-sum's duplicates come from
repeated values in the *input*, which the search cannot avoid encountering;
here they come from the *order of choices*, which the search controls.

## Sorting buys a break, not correctness

Once a candidate exceeds the remaining target, every later one does too — so
the loop can `break` rather than testing each in turn. Without sorting it has
to be a `continue`, which is still correct and explores more.

Worth being clear that this is a pruning optimisation and the answer does not
depend on it. `test_does_not_depend_on_candidate_order` checks that, and it is
also the test that catches sorting the caller's list in place.

## A target of zero is `[()]`

One combination — the empty one — not zero combinations. `[]` and `[()]` are
different answers and the second is correct: there is exactly one way to take
nothing and reach zero.

It falls out of the base case with no special handling, which is the tidy
outcome. Same distinction as the seeds in
[count the decodings](../count-the-decodings/notes.md), where "one way to
decode nothing" was the right value *inside* the recurrence — and there, unlike
here, the problem then overrode it for the empty input.

## What to take away

**In a backtracking search, the recursion's starting index is a specification,
not an implementation detail.** It decides whether you are enumerating
permutations, combinations, or combinations with repetition — and it is one
character. Before writing the body, decide which of the three you want and
write that call deliberately.
