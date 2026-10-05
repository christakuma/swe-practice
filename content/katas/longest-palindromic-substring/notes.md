# Longest Palindromic Substring — grow from centres

Revealed after grading. The problem is the classic one (LeetCode 5); the
wording above is ours. It is the clearest example in the library of a reframing
that deletes work rather than speeding it up.

## The obvious framing, and why it is the wrong one

Enumerate substrings, test each:

```python
for start in range(n):
    for stop in range(start + 1, n + 1):
        candidate = text[start:stop]
        if candidate == candidate[::-1] and len(candidate) > len(best):
            best = candidate
```

`O(n³)` — `O(n²)` substrings, each tested in `O(n)`. It asks "is this a
palindrome?" a quadratic number of times, and the answer is almost always no.

## The move

**Every palindrome has a centre.** So instead of testing candidates, grow
outwards from each possible centre and let the palindrome tell you where it
ends:

```python
def expand(low, high):
    while low >= 0 and high < len(text) and text[low] == text[high]:
        low -= 1
        high += 1
    return low + 1, high - low - 1        # (start, length)
```

`O(n²)` time, `O(1)` space. The palindrome test has vanished entirely — the
expansion *constructs* only palindromes, so nothing ever needs checking.

That is the pattern worth keeping: **when you are filtering a large candidate
set by a property, look for a way to generate only the candidates that have
it.** Here it turns a cubic search into a quadratic one and removes a function.

## Two kinds of centre

The bug that matters. `aba` is centred **on a character**; `abba` is centred
**on the gap between two**. A loop that only tries character-centres finds no
even-length palindrome at all, so `"cbbd"` comes back as `"c"`.

There are `2n - 1` centres, not `n`:

```python
for centre in range(len(text)):
    expand(centre, centre)        # odd length
    expand(centre, centre + 1)    # even length
```

`test_finds_an_even_length_palindrome` is the discriminating test, and every
odd-length case in the suite passes without even-centre handling — which is why
`"babad" -> "bab"` is a dangerous example to develop against.

## Keep (start, length), not the string

```python
if len(text[start:stop]) > len(best):     # O(n) copy per centre
```

Slicing a candidate at every centre to compare lengths turns each `O(1)`
bookkeeping step into an `O(n)` copy, and the whole algorithm back into
`O(n³)` — the bound the reframing was meant to beat. Carry the best as a
`(start, length)` pair and slice **once**, at the end.

`test_handles_a_long_string_without_cubic_work` uses `"a" * 3000`, the worst
case for centre expansion: every centre grows to the full width, so a per-centre
slice is at its most expensive.

## The tie-break is one character

`>` rather than `>=`. Centres are visited left to right, so with a strict
comparison a later equal-length palindrome never displaces an earlier one, and
"earliest on a tie" falls out for free. `test_returns_the_earliest_of_several_longest`
uses `"abacdc"`, where `"aba"` and `"cdc"` both have length three.

Worth noticing because it is the same shape as the `>` in
[best time to buy and sell](../best-time-to-buy-and-sell/notes.md): a tie-break
requirement satisfied by the comparison operator and the visit order together,
rather than by a special case.

## The `O(n)` answer exists

Manacher's algorithm does this in linear time, by reusing the palindrome
lengths already computed around a known centre to skip expansion it can prove
is redundant. It is genuinely clever and genuinely not worth writing from
memory in most situations — `O(n²)` with a tiny constant is fine for any string
you are likely to hold in memory, and the centre-expansion version is
explainable in two sentences.

Worth knowing it exists so you can say "and there is a linear algorithm if the
input warrants it", which is a more useful thing to know than the algorithm.

## What to take away

**Generate, don't filter.** The cubic solution tests a property; the quadratic
one is structured so the property holds by construction. When you find yourself
checking a predicate on nearly every candidate and nearly always failing,
the predicate is describing a structure you could be enumerating directly.
