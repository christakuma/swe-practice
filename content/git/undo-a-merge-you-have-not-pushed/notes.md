# Two ways to undo a merge, and the remote decides which

```
git reset --hard origin/main      # unpublished: move the branch back
git revert -m 1 <merge commit>    # published: add a commit that inverts it
```

They are not alternatives on a spectrum. Each is correct in exactly the
situation the other is wrong in, and the test is one command:

```
git log --oneline origin/main..HEAD
```

Anything that lists is yours and unpublished. The merge in this exercise is in
that list, so the branch can move.

## What `reset --hard` does here

```
before                          after reset --hard origin/main

c1                              c1
c2 <- origin/main               c2 <- origin/main, main
|  \                            |  \
|   s1 <- feature/search        |   s1 <- feature/search
M  <- main                      (M unreferenced, in the reflog)
```

The merge commit becomes unreachable. `feature/search` is untouched — it was
never the thing that moved. And `main` is byte-identical to what `origin` has,
so nobody can tell the merge happened.

## Why `revert -m 1` is wrong when the merge is local

`git revert` on a merge needs `-m` to say which parent's side to keep — `-m 1`
means "treat the first parent's line as the one that stays", which undoes
everything the branch brought in. It works, and it leaves two things behind:

1. **Two extra commits on `main`**: the merge, and the revert of it. Both
   describing something that should never have happened.
2. **`feature/search` still counts as merged.** The merge commit is still in
   `main`'s ancestry, so git believes the branch's commits are already
   incorporated. `git merge feature/search` later, when the branch *is*
   finished, says "Already up to date" and brings in nothing.

That second one is the trap. It is quiet, it comes back weeks later, and the fix
at that point is either reverting the revert or rebasing the branch onto a new
base. It is the standard reason "we reverted the merge and then the feature
never shipped" happens.

When the merge *has* been pushed, those costs are the price of not rewriting
shared history, and `revert -m 1` is right. The follow-up is then to know about
the already-merged problem in advance: revert the revert when the feature is
ready, or re-merge with `--no-ff` after resetting the branch.

## Why `--no-ff` is in the fixture

Without it, merging `feature/search` into a `main` that has not moved would be
a *fast-forward*: no merge commit at all, `main` just slides onto `s1`. That is
a different mistake with a different shape — and it is worth knowing that the
default is to fast-forward when it can, which is why `git merge` sometimes makes
a merge commit and sometimes does not.

A fast-forwarded "merge" is undone exactly the same way: `git reset --hard
origin/main`. There is simply no merge commit involved.

## Do not tidy up the branch at the same time

The second counter-example gets `main` perfectly right and deletes
`feature/search`. The merge commit was the only other thing pointing at `s1`,
and the reset just made that unreachable too — so both copies of the work go at
once, and recovering it needs the reflog rather than a branch name.

Undo one thing at a time. The merge was the mistake; the branch was not.
