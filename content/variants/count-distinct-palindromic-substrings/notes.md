# Counting things versus counting places

Revealed after grading. The "distinct" follow-up to "Palindromic Substrings"
(LeetCode 647).

The traversal does not change at all. Each of the `2n - 1` centres is expanded
exactly as before; the only difference is what happens on a hit:

```python
found.add(text[low : high + 1])     # was: count += 1
```

**The cost moved.** The standard version used `O(1)` extra space, because a
count needs no memory of what was seen. Distinctness needs exactly that
memory, so the set — and the slicing that feeds it — is unavoidable in this
approach. That is a fair observation to make before being asked.

"By position or by value?" is worth asking about any counting problem.
The standard kata said explicitly that identical substrings at different
positions count separately; this one says the opposite, and nothing else in
the wording changed.

(A string of length `n` has at most `n` distinct palindromic substrings — a
surprising fact, and the reason a structure called a palindromic tree can do
this in linear time. Not something to derive in an interview.)
