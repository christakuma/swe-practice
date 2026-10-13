# One difference to spend

Revealed after grading. This is "Implement Magic Dictionary" (LeetCode 676).

The standard store branches where the *pattern* says to: at a `.` it follows
every child, and everywhere else exactly one. This version has no pattern
character that says so. Any position might be the one that differs — but only
one of them.

So the walk carries the wildcard with it instead of reading it:

```python
def matches(node, index, spent):
    if index == len(word):
        return spent and node.is_word
    if spent:
        child = node.children.get(word[index])
        return child is not None and matches(child, index + 1, True)
    return any(
        matches(child, index + 1, character != word[index])
        for character, child in node.children.items()
    )
```

Before the difference is spent, every child is worth a look. The one that
matches costs nothing; each of the others costs the difference. After it is
spent, the search is an ordinary trie lookup. The branching happens once along
any path, so a search costs a few hundred steps however many words are stored.
At the sizes here a scan of every stored word passes as well; the trie is what
keeps working when the store is a dictionary.

## What the twist was testing

**"Exactly one" is not "at most one".** `return node.is_word` at the end of the
word is the standard store's line and it is wrong here by one word: the one
you searched for. A stored word is not its own neighbour, and it *is* found
when a different stored word is one letter away — both halves are in the
tests, and a solution that special-cases "is this word stored?" gets the
second one wrong.

The other common answer is a dict from each word with one position blanked
out — `h*llo`, `he*lo` — to the words that produce it. It works, costs `L`
keys per word, and has to solve the same problem at the end: a blanked key
that only the searched word itself produced is not a match.
