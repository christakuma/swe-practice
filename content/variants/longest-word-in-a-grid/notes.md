# Search in the order the answer is ranked

Revealed after grading. A "just the best one" variation on "Word Search II"
(LeetCode 212).

Listing every word present means nothing can be skipped, and the trie exists
to share work between them. Asking only for the longest changes the economics:
the moment a word is found, every word that ranks below it is irrelevant.

```python
for word in sorted({word for word in words if word}, key=lambda w: (-len(w), w)):
    if spelled(word):
        return word
```

Sort by the ranking, try in that order, stop at the first hit.

The trie that the list-everything version needs is not needed here. It
earns its place when many words must all be found and share prefixes; with an
early exit, most words are never searched for at all.

"Find the best" is often much cheaper than "find all", and the first thing to
try is ordering the candidates so that the first success ends the search.
