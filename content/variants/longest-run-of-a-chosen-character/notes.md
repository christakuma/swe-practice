# A fixed target makes the window simpler

Revealed after grading. This is "Max Consecutive Ones III" (LeetCode 1004) in
string form.

The standard version had a subtle step: the window is valid when its length
minus the count of its *most common* character is at most `k`, and tracking
that maximum is the part people get wrong. Fix the target and the subtlety
disappears — the only thing to count is how many characters are not it.

```python
if character != target:
    others += 1
while others > k:
    if text[start] != target:
        others -= 1
    start += 1
```

Sometimes a follow-up makes a problem easier, and the test is whether you
notice and simplify, or carry the harder machinery across because it is what
you have. A dict of counts works here. It is also thirty lines doing the job
of one integer.
