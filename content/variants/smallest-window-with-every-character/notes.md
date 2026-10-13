# The requirement came from the text

Revealed after grading. A variant of "Minimum Window Substring" (LeetCode 76)
often set as "smallest window containing all characters of the string
itself".

Two things are simpler than the standard problem, and both are easy to miss
by reusing its code unchanged.

**The target is computed, not given.** `needed = len(set(text))`. There is no
second string.

**Multiplicity is gone.** The standard version had to hold *enough* of each
character, so it compared counts. Here one of each is enough, and
completeness is just `len(counts) == needed` — provided a key is deleted when
its count reaches zero.

The loop shape is the standard one: grow until complete, then shrink while
still complete, and record on the way.

Passing `text` as both arguments to the standard solution is wrong, not just
wasteful: it would demand every character as many times as the whole text
contains it, and return the entire string.
