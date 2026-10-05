# Count the Decodings — Fibonacci with validity gates

Revealed after grading. The problem is the classic one (LeetCode 91); the
wording above is ours. The recurrence is [climbing stairs](../climbing-stairs/notes.md)
with conditions on the steps, and every difficulty in it is the digit `0`.

## The recurrence

A prefix's decodings either take its last digit alone or its last two digits
together:

```python
current = 0
if digit != "0":
    current += previous                      # one digit
if SMALLEST_PAIR <= pair <= LARGEST_LETTER:
    current += before                        # two digits
```

Same shape as climbing stairs — sum of the one or two counts behind you — with
each term **gated by validity**:

- one digit is usable when it is not `"0"`;
- two digits are usable when they read `10`–`26`.

`O(n)` time, `O(1)` space: the recurrence reaches back two places, so two
variables are all the history needed.

## The zero rules, which are the whole exercise

Two separate facts, both from the encoding having **no leading zeros**:

- a `0` can never stand alone, so `"0"` has no decodings;
- `"06"` is not `F`, because `06` is not how `6` is written.

Both fall out of the two gates with no special-casing. `10 <= pair` is doing
the leading-zero work — a pair starting with `0` reads below 10 — and
`digit != "0"` is doing the standalone work.

The nice consequence: **invalidity propagates arithmetically.** Once a count is
`0`, every later count is a sum of zeros, so an undecodable string reports 0
with no early return and no error path. `test_handles_an_undecodable_string_without_an_early_return`
uses `"1200"`, which is fine for three digits and then dies.

That is worth preferring to a validity scan. A single accumulator that becomes
zero and stays zero is less code than detecting the failure, and it cannot
disagree with the counting.

## The seeds are not symmetric

```python
before, previous = 1, 1
```

These look like the same value and mean different things:

- `previous` is the count for the **empty prefix**, and is `1` because there is
  exactly one way to decode nothing. That is what lets a valid first digit
  inherit a count of 1.
- `before` is `1` purely so a valid **two-digit opening** like `"12"` can reach
  past the empty prefix and count the both-digits reading once.

Seed either at `0` and the answer is silently halved for any input starting
with a two-digit letter — while every single-digit input still passes.
`test_counts_a_two_digit_opening_once` is that case.

And then the empty string returns `0`, **not** `previous`. "One way to decode
nothing" is bookkeeping *inside* the recurrence; the problem says the empty
string has zero decodings. Those two statements coexist and a solution that
conflates them returns 1.

**The general point: a DP seed is a claim about a subproblem, not about the
answer.** When the base case of the recurrence and the answer for the smallest
input disagree, both are right and you need the guard. This is where "it works
for n ≥ 1" bugs come from.

## The test worth copying

`test_counts_a_run_of_ones_like_fibonacci` checks `"1" * n` against
`1, 2, 3, 5, 8, 13, 21, 34`. Every adjacent pair is `11`, a valid letter, so
every prefix extends one way or two — the recurrence with both gates always
open, which is exactly Fibonacci.

A closed form is a much stronger expectation than a spot value: an off-by-one
in either seed shifts the whole sequence, which is visible immediately. And the
long test checks `"1" * 10000` against a Fibonacci computed independently — a
number with thousands of digits, held exactly, so anything that caps or mods
the count disagrees.

## What to take away

**Known recurrence, unknown gates.** Recognising "this is Fibonacci" gets you
the shape in seconds and tells you nothing about the hard part. The hard part
is the predicate on each term, and it comes from reading the specification
closely — here, that an encoding has no leading zeros, which is one sentence and
generates both of the problem's real cases.
