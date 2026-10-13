# Read the tie-break again

Revealed after grading. A convention change to "Top K Frequent Words"
(LeetCode 692).

The problem is identical except for one clause, and the clause decides the
output for any list with equal counts. `["pear", "apple", "fig"]` comes back
alphabetically under the standard rule and in arrival order under this one.

```python
ranked = sorted(counts, key=lambda word: counts[word], reverse=True)
```

A dict keeps its keys in insertion order and `sorted` is stable, so ties stay
in order of first appearance with no second key at all. (`reverse=True`
preserves stability too: equal elements keep their original relative order.)

Tie-breaks are where two correct-looking solutions disagree, and they are the
part of a problem statement most often skimmed. When the answer is a ranking,
find the sentence that says what happens to equals before writing anything.
