# Find what the transformation leaves alone

Revealed after grading. This is "Group Shifted Strings" (LeetCode 249).

Grouping anagrams and grouping shifts are the same program with a different
key. The skill is finding the key, and the question to ask is always: *what
does the allowed transformation not change?*

- Rearranging letters does not change their counts → sort, or count.
- Shifting every letter equally does not change the gaps between them →

```python
key = tuple((ord(letter) - ord(word[0])) % 26 for letter in word)
```

**The modulo is the bug.** Without it `"az"` has a gap of 25 and `"ba"` a gap
of -1, and they land in different groups although one is the other shifted by
a single step. It only shows on words that cross from `z` to `a`, which is
why it survives casual testing.

The key is called a canonical form or an invariant, and "group things that
are equivalent under X" almost always reduces to computing one.
