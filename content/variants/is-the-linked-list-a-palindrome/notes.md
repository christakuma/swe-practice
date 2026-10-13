# Three small problems in a row

Revealed after grading. This is "Palindrome Linked List" (LeetCode 234).

On a string, two indices walk in from the ends. A singly linked list has an
end you can reach and cannot leave, so that plan is dead on arrival. The
replacement is assembled from parts you already own:

1. **Find the middle** — slow and fast pointers, from cycle detection.
2. **Reverse the second half** — the standard reversal, started from the
   middle.
3. **Compare** the first half with the reversed second half, in step.
4. **Reverse the second half back.**

```
1 -> 2 -> 3 -> 2 -> 1            slow stops at the 3
1 -> 2 -> 3 <- 2 <- 1            after reversing from there
^                   ^
front               back         walk both until back runs out
```

## Where it goes wrong

**The odd middle.** With five nodes the halves are two and three. Compare
until the *reversed* half ends, and arrange for it to be the one that
includes the middle node — then the middle is compared with itself or not at
all, and no length arithmetic is needed.

**Step four.** The function was asked a question and has rearranged the
caller's data to answer it. Returning `False` from inside the comparison loop
is the natural thing to write and leaves the list in two pieces: the front
half now ends at the middle, and the back half is unreachable from the head.
Compute the answer, repair, then return.

**Recursion.** There is a neat recursive version that compares on the way
back up the call stack. It is `O(n)` space in frames and stops at about a
thousand nodes.

## What the twist was testing

Composition. No step here is new; each was a whole kata. Interview follow-ups
are very often like this — not a harder idea, but two or three familiar ones
that have to be made to fit together, with the joins (which half gets the
middle? who puts the list back?) being where the marks are.
