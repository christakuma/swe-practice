# The tie-break is the problem

Counting is a dict and one pass; nobody gets that wrong. What this kata is
actually about is expressing an ordering that runs in two directions at once:
counts descending, words ascending.

```python
sorted(counts, key=lambda w: -counts[w], reverse=True)   # wrong
sorted(counts, key=counts.get, reverse=True)             # wrong tie-break
sorted(counts, key=lambda w: (-counts[w], w))            # right
```

`reverse=True` reverses the *whole* comparison, including the tie-break, so
tied words come back in reverse alphabetical order. The fix is not another flag;
it is to put the direction into the key. Python compares tuples element by
element and only ever sorts ascending, so negating the count is how "descending"
is spelled.

For a key that cannot be negated — strings, say — the equivalent trick is two
stable sorts, applied in reverse order of priority:

```python
ranked = sorted(counts)                                  # alphabetical
ranked.sort(key=counts.get, reverse=True)                # then by count
```

Python's sort is **stable**, so the second sort preserves the first's order
within each group of equal counts. That is worth knowing: it is how you compose
orderings when a single key will not do, and it is the reason `list.sort` being
stable is a documented guarantee rather than an accident.

## `Counter.most_common` and why it is not the answer

`Counter.most_common()` is correct for counts and defines ties as insertion
order — which is a real guarantee, deliberately chosen, and useful when you want
"first seen wins". It is simply not the tie-break this problem specifies. Using
it and then re-sorting the ties is more code than sorting once.

## When to reach for a heap

Sorting is O(d log d) in the number of distinct words. A heap of size k is
O(d log k), which is the better complexity when k is small and the vocabulary is
large — a thousand most common words out of a million distinct ones.

```python
import heapq
heapq.nsmallest(k, counts, key=lambda w: (-counts[w], w))
```

`nsmallest` with the same key, because the key already encodes "best first".
One line, the better asymptotics, and worth being honest that for most inputs
the sort is faster in wall-clock terms — `nsmallest` has real per-element
overhead, and `sorted` is C all the way down.

The genuinely different approach is **bucket sort by count**: counts are bounded
by `len(words)`, so you can bucket words by count and walk the buckets
downwards, which is O(n) overall. It is the right answer when you need the
linear bound and you can live without the alphabetical tie-break — which you
cannot here without sorting each bucket, at which point you are back to sorting.
