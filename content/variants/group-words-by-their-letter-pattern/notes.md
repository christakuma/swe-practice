# Grouping is a key function and nothing else

Revealed after grading. The pairwise version of this is "Isomorphic Strings"
(LeetCode 205).

Every grouping problem has the same body:

```python
groups = {}
for word in words:
    groups.setdefault(key(word), []).append(word)
return list(groups.values())
```

What changes is `key`, and choosing it is the entire problem: it must be
equal for two words *exactly* when they belong together.

- **Anagrams**: same letters, any order → sort the letters.
- **Shifted strings**: same gaps between letters → the differences.
- **Letter patterns**: same repeats in the same places, any letters →
  rename each letter by the order it first appeared.

```python
first_seen = {}
key = tuple(first_seen.setdefault(letter, len(first_seen)) for letter in word)
```

`"egg"` and `"add"` are both `(0, 1, 1)`. `"gge"` is `(0, 0, 1)`.

## Why the key is enough

Comparing two words directly needs a mapping checked in *both* directions:
`"ab" -> "aa"` is consistent letter by letter (a→a, b→a) and still wrong,
because two letters collapsed into one. That two-way check is where pairwise
solutions go wrong.

The canonical form cannot make that mistake. `"ab"` is `(0, 1)` and `"aa"` is
`(0, 0)`; they are different tuples, and nothing needs checking.

## Small print

Build a tuple, not a string of digits. `"".join(str(n) ...)` makes the
eleventh distinct letter `"10"`, which is also what the second letter
followed by the first looks like.

## What the twist was testing

Whether the anagram solution was understood as "sort the letters" or as
"find the canonical form". Sorting is the wrong tool here in an instructive
way: it keeps exactly what this problem ignores (which letters) and discards
exactly what it needs (where they are).
