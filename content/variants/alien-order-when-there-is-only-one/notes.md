# Unique means never having a choice

Revealed after grading.

The standard problem has a tie-break — return the *smallest* valid alphabet —
and that tie-break is doing a lot of quiet work. `["ab", "ac"]` tells you
`b < c` and nothing about `a`, and the standard answer is `"abc"` as though it
had been deduced. This version asks the honest question: did the words
actually tell you the alphabet?

Kahn's algorithm already knows. At each step it holds the characters that have
nothing left to wait for:

- **none**, with characters still unplaced, is a cycle;
- **one** is a forced move;
- **two or more** is a choice — and either choice leads to a complete, valid,
  different alphabet.

```python
while len(available) == 1:
    character = available.pop()
    ...
return "".join(order) if len(order) == len(characters) else ""
```

One loop condition covers both ways of failing. The heap from the standard
solution is gone, because there is never a tie to break.

Another way to say the same thing: a topological order is unique exactly when
consecutive characters in it are joined by an edge — the order is a
Hamiltonian path through the graph. Kahn's with a queue of one is how you find
that out without looking for the path.

## What the twist was testing

Whether you check **every** step. `["ab", "ba", "bc"]` gives `a < b` and
`a < c`. One character is available at the start, so a check made only before
the loop says "unique" — and then `b` and `c` become available together.

And whether you noticed that "no valid order" and "too many valid orders" are
different failures that this problem happens to report the same way. An
unconstrained character is not an error in the input. It is the input not
saying enough.
