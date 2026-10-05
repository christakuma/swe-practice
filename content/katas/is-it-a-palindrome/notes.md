# Is It a Palindrome — skip in place, don't filter

Revealed after grading. The problem is the classic one (LeetCode 125); the
wording above is ours. The palindrome check is three lines everybody knows. The
exercise is the characters that do not count, and where you put the work of
ignoring them.

## The two solutions

```python
cleaned = [c.lower() for c in text if c.isalnum()]
return cleaned == cleaned[::-1]
```

Short, obviously correct, and `O(n)` space — it allocates a filtered sequence
and then a reversed copy of it. Two sequences the size of the input, to answer
a question whose answer is one bit.

```python
low, high = 0, len(text) - 1
while low < high:
    while low < high and not text[low].isalnum():
        low += 1
    while low < high and not text[high].isalnum():
        high -= 1
    if text[low].lower() != text[high].lower():
        return False
    low += 1
    high -= 1
return True
```

`O(n)` time, `O(1)` space. Same algorithm; the filtering has moved from *a data
structure* into *the traversal*.

**That is the transferable move.** When a problem says "ignoring X", the choice
is to build a copy without X or to skip X as you walk. The second is almost
always available and almost always what the space bound is asking for — and it
is the same instinct as the boundary pointers in
[read a matrix in spiral order](../read-a-matrix-in-spiral-order/notes.md):
represent what you are working on with indices rather than a copy.

## Three bugs, all in the skipping

**`if` instead of `while`.** There may be several ignorable characters in a
row. `"a,,,,a"` advances one position and then compares a comma against a
letter. `test_skips_runs_of_ignored_characters` is that case.

**Unguarded skip loops.** `".,"` has nothing to compare, so both pointers skip
past everything and run off the end. The `while low < high` at the top of the
body cannot save you, because the skipping happens inside an iteration that has
already begun — so each inner loop needs its own `low < high`.

**Hand-rolled classification.** `'a' <= c <= 'z' or '0' <= c <= '9'` looks
equivalent to `isalnum()` and is not: accented letters and non-Latin scripts
fall outside the range and get silently *skipped*, which turns a non-palindrome
into a palindrome. `test_handles_non_ascii_letters` uses `"éab"`, which must be
`False` and comes out `True` under a range check that discards the `é`.

`isalnum` and `lower` are defined over Unicode. Reaching past them to a range
comparison is the same class of mistake as the fixed 26-slot array in
[is it an anagram](../is-it-an-anagram/notes.md) — an alphabet assumption that
is correct until it isn't.

## Why the empty cases need no branch

The outer loop never runs, and `True` falls out. That is also the right answer
for `".,"` and `"   "`: an empty sequence reads the same both ways. Encoding it
as the natural result of the loop rather than as a guard at the top is the same
preference as seeding an accumulator with the default answer, from
[best time to buy and sell](../best-time-to-buy-and-sell/notes.md).

## A test that could not fail

Worth recording. The long-string test was first written as:

```python
assert is_palindrome(half + "z" + half[::-1]) is False      # passes as True
```

A single extra character inserted at the **exact centre** of a palindrome
leaves it a palindrome — the `z` has nothing to pair with. The assertion was
wrong, the content suite failed immediately, and the fix was to introduce the
mismatch at the front instead.

Two lessons, and the second is the general one. Adding a character to the
middle of a palindrome is a no-op, which is a fact worth knowing. And *a
negative test case has to be checked as carefully as a positive one* — it is
easy to construct an input you believe is a counter-example and that is
actually an example.

## What to take away

**"Ignoring X" is a traversal concern, not a preprocessing concern.** Filtering
first is the readable answer and costs space proportional to the input;
skipping as you go costs nothing and moves the complexity into loop guards you
then have to get right. The guards are the whole difficulty, and they are
guards about *running out of input*, which is the usual place pointer code
fails.
