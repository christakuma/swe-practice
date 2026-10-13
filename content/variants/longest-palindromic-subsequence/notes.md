# Compare the ends

Revealed after grading. This is "Longest Palindromic Subsequence"
(LeetCode 516).

The substring version is solved by standing on a centre and expanding, which
works because the characters of the answer are adjacent. A subsequence's
characters can be anywhere, so there is no centre to stand on. The useful
viewpoint is the opposite one: look at the two **ends**.

```
ends match    ->  2 + best(strictly between them)
ends differ   ->  max(best(without the first), best(without the last))
```

That is a table over every `(start, end)` stretch, filled shortest first.

There is a neat alternative: the answer is the longest common subsequence of
the text and its own reverse. It is true, it reuses a solution you already
have, and it is a good thing to mention — but be ready to say *why* it is
true rather than only that it works.

Substring versus subsequence changes the technique entirely, in both of the
places this library asks it. Contiguous: expand, slide, or reset to zero. Not
contiguous: a table over ranges or prefixes.
