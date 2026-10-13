# any becomes sum

Revealed after grading. The counting form of "Design Add and Search Words
Data Structure" (LeetCode 211).

The search has the same shape as before. A literal character follows one
child; a wildcard tries them all. The difference is one word:

```python
return sum(below(child, at + 1) for key, child in node.items() if key != _END)
```

`any` could stop at the first success. `sum` cannot, so a pattern of all
wildcards visits every node at that depth — there is no way round that, since
every one of those words is part of the answer.

What is preserved is the pruning that mattered: a literal character still
descends into exactly one child, so `count("12...")` looks only below `1`
then `2`.

**Duplicates.** Counting makes a bug visible that searching hid. If `add`
stores a repeated word twice, `search` is unaffected and `count` is wrong. A
trie avoids it for free — adding a word twice walks the same path.
