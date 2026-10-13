# The palindromes you used to count are now edges

Revealed after grading. This is "Palindrome Partitioning II" (LeetCode 132).

Counting palindromic substrings taught one technique: expand around each of
the `2n - 1` centres, and you visit every palindrome in the string once, in
`O(n^2)` total, with no table. This problem needs exactly that list — and
then does something with it.

Let `cuts[i]` be the fewest cuts for the first `i` characters. Every
palindrome `text[low..high]` is a statement about that table:

```python
cuts[high + 1] = min(cuts[high + 1], cuts[low] + 1)
```

"If you can cut up everything before `low`, one more cut gets you to
`high + 1`." With `cuts[0] = -1`, a palindrome starting at the beginning
costs zero.

So the counting loop survives intact and the `count += 1` in the middle of it
becomes one `min`.

## Why greedy fails

*Take the longest palindrome at the front, cut, repeat* handles most strings
people test by hand. `"abaab"`: the longest palindromic prefix is `"aba"`,
leaving `"ab"` — two cuts. But `"a" | "baab"` is one. A long first piece can
break up a longer palindrome that needed its last character.

There is no local rule, which is what makes it dynamic programming: the best
cutting of a prefix has to be known for *every* prefix.

## Why the order of the loop is safe

`cuts[low]` is read while expanding around `centre`, and `low <= centre`. It
is final once every palindrome ending at `low - 1` has been processed, and all
of those have centres strictly left of `centre`. A different loop order —
longest palindromes first, say — reads entries that are still at their
worst-case value.

## What the twist was testing

Whether expand-around-centre was understood as *an enumeration* or as *the
answer to one question*. It is a way to visit every palindrome cheaply, and
counting them was the least interesting thing to do on the visit.
