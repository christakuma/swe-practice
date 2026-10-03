# `ORIG_HEAD` is git's undo button for a bad pointer move

Before any command that moves a branch wholesale — `rebase`, `merge`, `reset`,
`pull` — git writes the current commit to `.git/ORIG_HEAD`. It is a one-slot
history: the position *immediately before* the last such operation.

```
git reset --hard ORIG_HEAD
```

That is the undo for a rebase, a bad merge, a `reset` to the wrong place, and a
`pull` that merged something you did not want. One command, nothing to look up.

The one-slot part matters. `ORIG_HEAD` is overwritten by the *next* operation
that moves the branch, so it is good for undoing the thing you just did and not
for anything older. For older, there is the reflog, which keeps every position:

```
git reflog                      # every value HEAD has had, newest first
git reset --hard HEAD@{3}        # the fourth entry down
```

`ORIG_HEAD` is the convenient case of the reflog. Both are local — they live in
your `.git` and nobody else can see them, which is also why they are not a
substitute for pushing.

## Three ways to the same commit here

In this exercise the pre-rebase tip is reachable three ways, and it is worth
noticing that they agree:

| route | what it means |
|---|---|
| `ORIG_HEAD` | where the branch was before the rebase |
| `HEAD@{1}` | the previous position of `HEAD` in the reflog |
| `origin/feature/mfa` | what the remote still holds, because you have not pushed |

`git rev-parse ORIG_HEAD origin/feature/mfa` prints two hashes. When they match,
the recovery is unambiguous — and when they do *not*, that is the far more
interesting situation: it means someone else has pushed since you last fetched,
and you need to work out what before you reset anything.

## Why the rebase was wrong here and right elsewhere

Nothing is wrong with the rebase as a command. What was wrong is that the branch
had been **pushed**, and a colleague had pulled it. The rebase replaced `f1` and
`f2` with new commits that have the same diffs and different hashes, so:

- their clone holds two commits that are no longer in the branch
- the next `git pull` sees divergent histories: two commits on each side with
  identical content
- a default merge pull resolves it by *merging*, which reinstates the originals
  and applies every change twice

Force-pushing would make `origin` agree with you and does nothing about their
clone — it just removes the last copy of what they have, which is why it is the
one irreversible action available in this exercise.

## Why merging the old tip back is not the fix

```
git merge origin/feature/mfa
```

This brings `f1` and `f2` back into the branch, so `originals-recovered` passes.
It also keeps `f1*` and `f2*`, the rebased copies. The branch now contains both
versions of every change, joined by a merge commit:

```
m1
f1*  f1
f2*  f2
  \  /
   M   <- feature/mfa
```

`git log` reads as if the feature was implemented twice. The diff against `main`
may well be correct, because the second application of a change that is already
present is usually a no-op — so tests pass and the history is nonsense. That
makes it the worst of the wrong answers here: it is the one you might not notice.

## The general shape

Whenever a single command has moved a branch somewhere you did not want:

1. **Do not push anything.** While the remote still holds the old state, you
   have a second copy and nobody else is affected yet.
2. `git log --oneline --decorate --all` to see where everything is now.
3. `git show ORIG_HEAD` to confirm the previous position is what you want.
4. `git reset --hard ORIG_HEAD`.

Step 1 is the one that does the work. Nearly every git mistake is local and
cheap until it is published.
