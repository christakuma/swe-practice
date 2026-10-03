# Greedy fails because an early choice is unjudgeable

Match the longest word you can, repeat. On `"cars"` with
`["car", "ca", "rs"]`:

```
longest match at 0 is "car"  ->  "s" left, not a word  ->  fail
shorter match      "ca"      ->  "rs" left, a word     ->  success
```

Greedy has no way back. And the failure is not fixed by preferring the *shortest*
match either — `"aaa"` with `["a", "aaa"]` works both ways, but
`["aa", "aaa"]` on `"aaaaa"` needs `aa + aaa`, which neither "always shortest"
nor "always longest" produces reliably.

The general reason: the goodness of a cut at position `i` depends on the entire
rest of the string. Nothing local decides it, so you have to consider all cuts —
and that is a DP, not a greed.

## The table

```
reachable[0] = True                       # the empty prefix needs no words
reachable[i] = any(reachable[j] and text[j:i] in dictionary
                   for j in range(i))
```

Each position answers "can the string up to here be split?". It only ever reads
earlier positions, so one forward pass fills it, and the answer is
`reachable[len(text)]`.

```
"cars", {"car", "ca", "rs"}

i        0     1      2      3     4
prefix   ""    "c"    "ca"   "car" "cars"
reach    T     F      T      T     T
                      ^ "ca"       ^ "rs" from position 2
```

Note position 3 is also reachable (via `"car"`) and is a dead end — nothing
extends it to 4. The table keeps both routes without having to choose, which is
exactly what greedy cannot do.

## Why the dictionary is a set

The inner loop asks "is this slice a word" once per pair of positions. With a
list that is a linear scan each time, multiplying everything by the dictionary
size. With a set it is a hash lookup, and the cost of the slice itself dominates.

Bounding the inner loop by the **longest word** is the other easy win:

```python
for start in range(max(0, end - longest), end):
```

On real text — short words, long string — that turns O(n²) slices into O(n × k)
of them, so O(n × k²) once the slicing and hashing of each is counted. With k
small and n large that is the difference between a toy and something you could
point at a document.

## The exponential version, and why memoising it is the same thing

```python
def can(rest):
    if not rest:
        return True
    return any(can(rest[len(w):]) for w in words if rest.startswith(w))
```

Correct, and it re-solves the same suffix once per route that reaches it. The
suite's `"aaa...ab"` case is built for this: every prefix is splittable and
nothing covers the final `b`, so the search explores astronomically many splits
before concluding failure.

`@functools.cache` on that function makes it polynomial — the same O(n × k²) —
and is the top-down spelling of the same table. Worth knowing both directions — top-down is usually
easier to derive, bottom-up is usually easier to make space-efficient.

## Variants

- **return the actual split** → store, per position, which `j` worked, and walk
  back
- **all possible splits** → the same table, but the answer is now exponential in
  size, so the enumeration has to be lazy
- **the cheapest split** by some word cost → `min` instead of `any`, and this
  becomes exactly [coin change](../coin-change/notes.md) over string positions

That last equivalence is the one worth seeing: word break is coin change where
the coins are substrings and the amount is a string.
