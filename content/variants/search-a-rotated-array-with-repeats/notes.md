# When three values tie, the comparison has nothing to say

Revealed after grading. This is "Search in Rotated Sorted Array II"
(LeetCode 81).

The standard search works because one half of any window is sorted, and
comparing the first value with the middle one says which. Repeats break
exactly that comparison:

```
[1, 0, 1, 1, 1]      first == middle == last
[1, 1, 1, 0, 1]      the same three values, the 0 on the other side
```

Nothing visible distinguishes the two, so no half can be thrown away. What
*can* be thrown away is the two ends: they equal the middle, and the middle is
not the target.

```python
if numbers[low] == numbers[mid] == numbers[high]:
    low += 1
    high -= 1
```

That one case is the entire difference, and it is why the worst case becomes
`O(n)`. This is not a weakness of the method. A list of a million 1s with one
0 in it cannot be searched without, in the worst case, looking at most of it —
the follow-up question "what is the complexity now, and why?" is the real
content of the exercise.
