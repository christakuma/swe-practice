# Count Palindromic Substrings — same generator, different consumer

Revealed after grading. The problem is the classic one (LeetCode 647); the
wording above is ours. It is deliberately placed right after
[longest palindromic substring](../longest-palindromic-substring/notes.md),
because the pair makes a point that neither makes alone.

## The whole difference

Centre expansion, identical to the previous kata:

```python
def count_from(low, high):
    found = 0
    while low >= 0 and high < len(text) and text[low] == text[high]:
        found += 1                       # <- the only new line
        low -= 1
        high += 1
    return found
```

In the longest-substring kata, each centre produced **one** answer: its widest
palindrome. Here every *step* of the expansion is an answer, because each
successful step is itself a distinct palindromic substring — one character
wider at each end than the one before.

So the count happens **inside** the loop. Same generator, consumed differently:
one problem wants only the final value, the other wants all of them.

**That is worth noticing as a habit.** When two problems share a structure, the
useful question is not "how do I solve this one" but "what does this one do
with the thing I already built". Expansion from centres enumerates every
palindrome in the string; `max` over that stream and `len` over that stream are
both one line.

## The bug is the same bug

Both centre kinds: `n` character-centres and `n - 1` gap-centres. Count only
the odd ones and `"aaa"` comes out as **4** instead of 6.

That is worse than the analogous failure in the previous kata. There, missing
even centres returned `"c"` for `"cbbd"` — visibly wrong. Here it returns a
*number*, and 4 is as plausible as 6. Nothing about the output suggests a bug.

`test_counts_even_length_palindromes` is the discriminating test, and
`test_counts_a_fully_uniform_string` is the one that makes it unmissable: every
substring of a uniform string is a palindrome, so the answer has a closed form,

```
n(n + 1) / 2
```

and the test checks it for every size from 1 to 11. A closed-form expectation is
much stronger than a spot value — it cannot be satisfied by a solution that is
merely off by a consistent amount.

## Nothing needs deduplicating

The two `"aa"`s in `"aaa"` are different substrings, so the answer is 6 rather
than 3. Each palindrome is found by **exactly one centre**, so each is counted
exactly once with no bookkeeping at all.

This is worth being explicit about because the instinct on seeing "count the
substrings" is to reach for a set, and a set here is both slower and **wrong**:
`set` of distinct strings reports 3 for `"aaa"`. `test_counts_overlapping_palindromes`
exists for that solution.

Compare with [three sum](../three-sum-to-zero/notes.md), where deduplication
*was* required and the skips were most of the work. The difference is entirely
in the problem statement — "distinct triples" against "substrings at different
positions count separately" — and reading which one you have been given is the
actual skill.

## The long test had to be resized to mean anything

`test_counts_a_long_uniform_string_without_cubic_work` originally used a
3000-character string and claimed the cubic solution "does not finish". It
finishes in **5.4 seconds**, against a 15-second limit — so the enumerate-and-
slice solution passed the kata, and the claim was simply false.

At 5000 characters the cubic version takes **30.9s** and centre expansion takes
**1.3s**, which is two times over the limit against eleven times under it. That
is the margin a timing test needs in *both* directions: enough to fail the slow
solution on a fast machine, and enough to pass the fast one on a loaded CI box.

The general point, and the reason this is in the notes rather than quietly
fixed: **a timing test is a claim about two numbers, and writing down only the
asymptotics does not establish either of them.** `O(n³)` beats `O(n²)` in the
limit and not necessarily at the size you chose.

## What to take away

**A one-line change to the consumer is often the whole difference between two
problems.** Having built an enumerator, ask what else it enumerates.

And the quieter lesson: **a wrong answer that is a number is harder to notice
than a wrong answer that is a string.** When the output carries no structure,
lean on expectations that have structure — closed forms, invariants, agreement
with an independent oracle — rather than on values you believe are right.
