# Throw away three different words at a time

Revealed after grading. This is "Majority Element II" (LeetCode 229), an
instance of the Misra–Gries algorithm.

Top-k-frequent counts everything and then selects. If all you want is the
words above a fixed *fraction*, counting everything is more than the
question needs — there can only be two such words, and two words do not
need a table.

## The cancellation idea

Start with the one-candidate version, for a strict majority. Pair up
*different* words and discard both; whatever is left when you can pair no
more must be the majority, because a word with more than half the list
cannot run out of copies before its opponents do.

For thirds, discard **three different words at a time**. Each discard
removes at most one copy of any word, and there can be at most `n / 3`
discards — so a word with more than `n / 3` copies survives.

Two slots implement it:

```python
if word == first:            first_count += 1
elif word == second:         second_count += 1
elif first_count == 0:       first, first_count = word, 1
elif second_count == 0:      second, second_count = word, 1
else:                        first_count -= 1; second_count -= 1
```

The last branch is the discard: this word and one copy of each candidate.

## Why the second pass

The guarantee runs one way. *If* a word is frequent enough, it ends up in a
slot. A slot being occupied proves nothing: `["a", "b", "c", "d"]` ends with
two candidates, each of which appears once. The counters are not counts
either — they are what is left after cancellation.

So count the two candidates for real. Still `O(1)` space: two more integers.

## Order of the branches

Check for a match with **either** candidate before checking for an empty
slot. Otherwise a word already sitting in the first slot gets installed in
the second as well, and is reported twice or crowds out the other answer.

## What the twist was testing

Noticing when a question is weaker than the one you know how to answer. "The
top k" needs every count. "Everything above a threshold" does not, and the
gap between them is the whole of streaming algorithms: bounded memory, one
or two passes, and an answer that is exact because the question was chosen
to allow it.
