# The answer only shrinks

Every candidate prefix is a prefix of the first word, and each new word can only
make it shorter. That monotonicity is what makes one pass enough — there is no
backtracking, and the loop can stop the instant the candidate is empty.

```
["flower", "flow", "flight"]

candidate = "flower"
vs "flow"    -> "flowe", "flow"      (shrink until it is a prefix)
vs "flight"  -> "flo", "fl"          (shrink again)
answer "fl"
```

## The two standard shapes

**Shrink a candidate** (above). Simple termination, and `startswith` does the
character comparison in one call.

**Vertical scan**: compare column 0 across all words, then column 1, and stop at
the first mismatch *or* at the first word that has run out of characters.

```python
for column in range(len(words[0])):
    letter = words[0][column]
    for word in words[1:]:
        if column == len(word) or word[column] != letter:
            return words[0][:column]
return words[0]
```

Better on its best case — `["dog", "racecar"]` stops after one comparison
instead of scanning a whole word — and it is where the off-by-one bugs live.
`column == len(word)` is the check that exists only because a word can be
shorter than the column you are reading, and leaving it out is an
`IndexError` on exactly the input the suite tests for.

Both are O(n·m) in the worst case: n words, m the length of the eventual prefix.

## Two edge cases worth being deliberate about

- **empty list** → `""`. `words[0]` raises without a guard, and it is the input
  most likely to be missing from a first draft.
- **an empty string among the words** → `""`, immediately. Nothing can be a
  prefix of `""` except `""`. The shrink version reaches this by cutting the
  candidate all the way down; the early return makes it one step.

## When the problem is bigger than this

For *repeated* queries against a fixed set of words — "which of my million
words start with this?" — the data structure is a **trie**, and the longest
common prefix of the whole set is the path from the root down to the first node
with more than one child or a word ending. Building it is O(total characters),
and it then answers prefix questions in O(length of the query).

Worth knowing where the line is: for one question about n words, the trie costs
more to build than the scan costs to run. The scan is not a worse algorithm, it
is the right one for a single query.
