# Once order is free, only the counts are left

Revealed after grading. "Longest Palindrome" (LeetCode 409), asked for the
string and not just its length.

Finding the longest palindromic *substring* is about position: centres,
expansion, where things are. Allow rearrangement and position stops
mattering at all. What remains is how many of each character you have.

## Length

A palindrome is its own mirror image, so characters are used two at a time,
one on each side. One character may stand alone in the middle.

- each character gives `count // 2` pairs;
- if any character has an odd count, one of them can be the centre.

The classic slip is treating "odd count" as "unusable". Three a's are one
pair *and* one spare.

## Which one

A longest palindrome must use every pair, so the only choices are the order
of the left half and which spare character is the centre.

Strings of the same length compare from the left:

1. The **left half** comes first. Sorted ascending is the smallest
   arrangement there is.
2. The **centre** comes next. The smallest spare character.
3. The **right half** is the left half reversed. No choice.

```python
half = "".join(ch * (counts[ch] // 2) for ch in sorted(counts))
spare = [ch for ch, count in counts.items() if count % 2]
return half + min(spare, default="") + half[::-1]
```

The centre is the *smallest* spare, not the most plentiful one. In `"abbb"`
there are more b's, but the b's are already supplying the pair; the choice is
between a spare a and a spare b, and `"bab"` beats `"bbb"`.

## What the twist was testing

Recognising when a constraint was carrying the difficulty. "Contiguous, in
the original order" is what made the standard problem `O(n^2)`. Remove it
and the problem is a tally and a sort — and an interviewer who relaxes a
constraint is usually checking whether you will notice that the problem got
*easier*, or keep reaching for the machinery you just built.

The second half is the tie-break. "Any longest palindrome" is one line;
"the first in sorted order" needs an argument about which positions are
compared first, and it is worth saying that argument aloud.
