# Deletion is the half nobody practises

Revealed after grading. "Implement Trie" (LeetCode 208) with the operation
its standard form leaves out.

Clearing the end-of-word flag is the obvious removal, and it is half right:
`contains` becomes false and `starts_with` goes on reporting a prefix that no
stored word has. The nodes are still there.

The fix is to make every node know how many words run through it:

```python
child.passing -= 1
if child.passing == 0:
    del node.children[character]
    return True
```

A node at zero is on no word's path, so it — and everything beneath it — can
go. A node above zero is shared, and stays.

**Check before you change.** Removing a word that is not stored must leave
the counts alone. Decrementing on the way down and discovering part-way that
the word is absent corrupts every count already touched.

Insert-only versions of a structure hide its invariants. Asking for deletion
is how an interviewer finds out whether you know what they are.
