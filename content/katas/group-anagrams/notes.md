# The question is what the key is

Every "group things that are equivalent" problem reduces to finding a
**canonical form**: a value you can compute from one item alone, equal for two
items exactly when they belong together. Once you have one, the grouping is a
single pass into a dict and there is nothing left to think about.

For anagrams, sorted letters is a canonical form:

```
"eat" -> "aet"
"tea" -> "aet"
"tan" -> "ant"
```

The alternative that occurs to everyone first — compare each word against every
other — is quadratic in the number of words, and it is quadratic *because* it
keeps asking a question about pairs that could have been answered about
individuals.

## Keys that look right and are not

- **`set(word)`** loses counts. `"aab"` and `"abb"` have the same letter set and
  are not anagrams. This is the mistake the suite tests for specifically,
  because it passes every obvious case.
- **`len(word)`** is necessary and nowhere near sufficient.
- **sum of character codes** collides constantly: `"ad"` and `"bc"` both come to
  197. A hash that collides is not a canonical form, it is a filter — you would
  still have to compare within each bucket.
- **a product of primes per letter** actually works and is a genuinely nice
  trick: assign each letter a prime, multiply. Equal products mean equal
  multisets, by unique factorisation. It is O(k) rather than O(k log k) per word,
  and it overflows in most languages that are not Python.

The honest alternative to sorting is a **count tuple** — 26 counts, or a
`tuple(sorted(Counter(word).items()))`. O(k) per word instead of O(k log k), and
worth reaching for when the words are long. For words of five letters, sorting
wins on clarity and nobody can measure the difference.

## Why the ordering is free

Python dicts have preserved insertion order since 3.7, as a **language
guarantee** rather than a CPython implementation detail. So:

- `groups.setdefault(key, []).append(word)` appends words within a group in
  input order
- `list(groups.values())` yields groups in the order each key was first inserted

Both halves of the required ordering, with nothing sorted afterwards. Worth
knowing precisely because the instinct is to distrust it and sort to be safe,
which adds an O(n log n) step to buy a property you already had.

## Complexity

O(n · k log k) time for n words of length k — the sort per word dominates — and
O(n · k) space for the keys and the groups. The count-tuple variant is O(n · k)
time, which matters only when k is large.
