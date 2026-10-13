# You were asked a smaller question

Revealed after grading. This is "One Edit Distance" in its at-most-one form
(LeetCode 161; *Cracking the Coding Interview* 1.5).

The edit-distance table answers "how far apart are these strings?" for any
distance, at `O(n * m)`. This question is whether the distance is 0 or 1, and
that is a much weaker thing to ask — weak enough to answer in one pass.

```python
if abs(len(source) - len(target)) > 1:
    return False
...
if len(shorter) == len(longer):
    return shorter[at + 1 :] == longer[at + 1 :]   # replacement
return shorter[at:] == longer[at + 1 :]            # insertion
```

Find the first disagreement; after it, everything must line up.

**The lengths do half the work.** Equal lengths rule out insertion; lengths
one apart rule out replacement; anything more rules out everything. Checking
that first turns three cases into one branch.

Reaching for the general algorithm when a special case was asked is one of
the commonest ways to lose time in an interview. When the question has a
small constant in it — one edit, two missing, at most k — check whether the
constant makes the problem easy before generalising.
