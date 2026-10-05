# Longest Run After K Replacements — an invariant allowed to be wrong

Revealed after grading. The problem is the classic one (LeetCode 424); the
wording above is ours. The sliding window is routine. The reason this kata is
worth doing is a counter that is deliberately permitted to hold a stale value,
and the argument for why that is safe.

## The condition

A window can be made uniform within budget exactly when:

```
len(window) - (count of its most common character) <= k
```

Everything that is not the most common character has to be replaced, so that
subtraction *is* the cost. And the condition gets **harder** to satisfy as the
window grows, which is the property that licenses a sliding window at all:
grow on the right, shrink from the left only while the condition fails.

```python
for right, character in enumerate(text):
    counts[character] = counts.get(character, 0) + 1
    most_common = max(most_common, counts[character])

    while (right - left + 1) - most_common > k:
        counts[text[left]] -= 1
        left += 1

    best = max(best, right - left + 1)
```

Each end moves forward at most `n` times, so `O(n)` time.

## The stale counter

`most_common` is **never decreased.** After the left edge moves past the last
copy of the majority character, it is simply wrong — larger than any count
actually in the window.

The answer is still correct. The argument:

> A stale `most_common` only makes the condition look *easier*, so the window
> can be left wider than it should be. But `best` only ever records the current
> width, and the width only grows when a new character arrives. For `best` to
> exceed the true answer, some window would have to genuinely contain
> `most_common` copies of one character — which is exactly what makes a window
> valid. So the relaxed test cannot raise the maximum; it can only delay
> shrinking.

Said more compactly: the answer is a maximum over valid windows, and loosening
the validity test cannot increase that maximum unless a genuinely valid wider
window exists.

**This is the thing to take away, and it is not the performance.** Recomputing
`max(counts.values())` every step costs `O(alphabet)` and is completely fine —
if the alphabet is 26, the "optimisation" saves nothing worth having. What is
worth having is the *shape of the reasoning*: an invariant held deliberately
loose, justified not by being true but by what the value is used for.

That technique is real and easy to misapply. It works here because the stale
value only ever relaxes a constraint whose relaxation cannot affect the result.
Change `best` to record something else — the window's contents, say, or the
number of valid windows — and the same code becomes wrong. Which is why the
reference docstring states the argument rather than asserting the trick, and
why `test_agrees_with_brute_force_on_every_binary_string` sweeps every string
of length ≤ 9 against an oracle that recounts each window from scratch. The
claim is *verified*, not believed.

## The window that does not shrink

The opposite bug is more common and much simpler: never shrinking at all, which
reports `5` for `longest_run("ABCDE", 1)`. The window must contract whenever
the condition fails, and `test_does_not_count_a_window_it_cannot_afford` is
that case.

Worth noticing that both bugs are about shrinking — one shrinks too late by
design and is fine, the other never shrinks and is broken. The difference is
entirely in whether `best` can observe the over-wide window.

## Why a dict and not 26 slots

The usual presentation assumes uppercase letters and indexes `[0] * 26`. The
prompt here does not constrain the alphabet, and
`test_handles_non_letter_characters` uses `"..::.."` and `"1223"`. Same
judgement as in [is it an anagram](../is-it-an-anagram/notes.md): the array is
right when the constraint is written down, and a very common way to ship a bug
when it was assumed.

## What to take away

**A sliding window needs a condition that is monotone in the window's size.**
That is the precondition, and checking it is the first thing to do — grow-and-
shrink is only valid when growing can break the condition and shrinking can fix
it. Here it holds; in problems where it does not, the window silently misses
answers.

And: **when you let a value go stale on purpose, write down the argument.**
Not because reviewers demand it, but because the argument is what tells you
which later change breaks it.
