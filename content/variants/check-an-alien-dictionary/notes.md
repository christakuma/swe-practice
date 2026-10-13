# The easy direction

Revealed after grading. This is "Verifying an Alien Dictionary"
(LeetCode 953).

Deriving an alphabet from sorted words needed a graph and a topological sort.
Checking a list against a given alphabet needs neither: sortedness is a claim
about neighbours, and each pair is one comparison.

```python
rank = {character: position for position, character in enumerate(alphabet)}
keys = [[rank[character] for character in word] for word in words]
return all(first <= second for first, second in pairwise(keys))
```

Translating to lists of positions is the trick. Python compares lists the way
a dictionary compares words — element by element, with a proper prefix
smaller — so both rules come for free.

**The prefix rule survives the change of alphabet.** `"apple"` before `"app"`
is wrong in every alphabet. Code that only looks for the first differing
character, and finds none, has to decide something; deciding "in order" is
the bug.
