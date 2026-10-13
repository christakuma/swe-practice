# The closest word is next to you in the dictionary

Revealed after grading. "Shortest Unique Prefix" — the autocomplete question.

## What decides an answer

A prefix of length `p` fails to single a word out when some other word has
the same first `p` characters. So what matters for each word is one number:
the **most** leading characters it shares with any other word. The answer is
one more than that — or the whole word, if there is no "one more".

Finding that number by comparing with every other word is `O(n^2)`.

## Sorting finds it

Sort the list. Words with a common prefix end up in one unbroken block, so
the word that shares the most with you is directly before or directly after
you. Nothing further away can share more than they do.

```python
order = sorted(range(len(words)), key=words.__getitem__)
shared = [common(words[a], words[b]) for a, b in pairwise(order)]
...
need = max(before, after) + 1
prefixes[position] = words[position][:need]
```

Two comparisons per word instead of `n`.

`order` holds positions, not words, because the answers are wanted in the
original order and sorting the words themselves would lose it.

## The cases that take care of themselves

- **A word that another starts with.** `"car"` and `"cart"` share three, so
  `need` is four, and `"car"[:4]` is `"car"`. The slice stops at the end.
- **A word that appears twice.** The two copies sort next to each other and
  share everything. Same slice, same result.
- **A word alone.** It shares zero with nobody, `need` is one, and it gets
  its first letter.

The one way to break the second case is to be tidy and call `set(words)`
first. The duplicates were information.

## The trie version

Build a trie in which every node counts the words passing through it. Walk
each word down until the count is 1; that depth is the answer.

It is the answer an interviewer usually has in mind, and it is `O(total
characters)` with no sort. In Python the sort is shorter, uses far less
memory than a dictionary per character, and is fast because the comparisons
happen in C. Offer both, and say which you would ship.

## What the twist was testing

The standard problem asks what a group of words has in common. This asks
what sets each one apart, and the naive reading of that is all pairs. The
skill is seeing that "closest to me" has a cheap meaning once the list is in
the right order — the same move as finding the closest pair of numbers by
sorting them first.
