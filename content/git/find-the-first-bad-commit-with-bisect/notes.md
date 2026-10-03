# Bisect is a binary search you drive one answer at a time

`git bisect` does not know what "broken" means. You give it one commit that is
bad and one that is good, and it checks out the middle of the range; you look,
and say `good` or `bad`; it halves again. Nine commits take three questions
instead of eight.

```
git bisect start
git bisect bad                 # HEAD is broken
git bisect good HEAD~8         # the oldest commit was fine
# -> git checks out the midpoint
cat limits.yaml                # look
git bisect good                # or bad
# ... repeat until one commit is left
git bisect reset               # back where you started
```

The two bounds are the part people get wrong, and they are not symmetric: `good`
is a commit you are *certain* about. Guessing a `good` that is actually bad
makes the whole search point at the wrong place, confidently.

## Why this exercise is not a `grep`

Searching history for a bad value is often the faster tool — and it is the right
tool when such a value exists. Here it does not. Every number in `limits.yaml`
is plausible on its own; what is wrong is the relationship between two of them.
No `git log -S` can find that, because no commit contains the string "wrong".

That is the real dividing line:

| the symptom is | the tool |
|---|---|
| a line of text that appeared or vanished | `git log -S` / `git log -G` (the pickaxe) |
| a line's current content being wrong | `git blame` |
| a *behaviour* you can test | `git bisect` |

Bisect is the one that scales to "I do not know what I am looking for", which is
most real regressions. The cost is that you have to be able to decide good or
bad at each step — which, when the decision is "do the tests pass", is where
`git bisect run` comes in.

## `git bisect run`, the version you will actually use

```
git bisect start HEAD HEAD~20
git bisect run pytest tests/test_capacity.py
```

Any command whose exit status says good (0) or bad (non-zero) works. Git then
runs the whole search unattended and prints the first bad commit. That turns
"an afternoon of checking out commits" into a coffee break, and it is the reason
a regression test written *before* the bisect pays for itself immediately.

Exit code 125 is the special one: it means "cannot test this commit — skip it",
for a commit that does not build at all.

## Leaving the bisect running

A bisect checks commits out, so for its whole duration you are on a detached
HEAD with `refs/bisect/*` and `.git/BISECT_START` in place. `git bisect reset`
ends it, restores the branch you started on, and cleans those up.

`git checkout main` looks like it does the same thing. It reattaches HEAD and
leaves the bisect state behind, so git still believes a search is in progress —
and the next `git bisect start` either complains or silently continues the old
one. That is why `back-on-main` and `back-on-a-branch` are separate checks here:
one of them passes for the half-finished cleanup and the other does not.

## Recording the answer

When the search finishes, git prints the first bad commit and leaves `HEAD` on
it. That is the only output — once you reset, the result exists nowhere but your
scrollback. So capture it while you are standing on it:

```
git tag first-bad          # tags HEAD
git bisect reset
```

A tag, a branch, or a line in the ticket. The habit matters more than which: the
expensive part of a bisect is the search, and losing the hash means doing it
again.

`git bisect log` also prints the whole session as a replayable script, and
`git bisect replay <file>` re-runs it — useful when you realise you answered one
step wrong and do not want to start over.
