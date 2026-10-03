# A stash is a commit with no branch

`git stash push` makes two commits — one for the index, one for the working tree
— joins them under a merge commit, points `refs/stash` at it, and then resets
your working tree to `HEAD`. That is why your changes disappear from
`git status` and why they are completely safe: they are objects in the database
like any other commit.

```
c1 ---- c2 ---- c3   <- main

   W     (refs/stash -> W, parents: c1 and the index commit)
```

`refs/stash` is a ref, so it has a reflog, which is what makes `stash@{0}`,
`stash@{1}` and so on work. The stack is just reflog entries on one ref.

Two consequences worth having:

- `git log` will never show you a stash. It walks from branches and tags.
  `git stash list` reads `refs/stash`'s reflog instead.
- A stash is not tied to a branch. Pop it on a different branch and git applies
  the change there, which is sometimes exactly what you want and sometimes how
  a change ends up on the wrong branch.

## `apply` versus `pop`

```
git stash apply    # apply the change, keep the stash entry
git stash pop      # apply the change, delete the stash entry
```

That is the only difference. `pop` is what you want nine times in ten;
`apply` earns its keep when you want the same change on two branches, or when
you are not yet sure it applies cleanly and would rather keep the safety copy
until you are.

Leaving an entry behind after committing the change is the mistake this exercise
checks for. It is quiet: the work is in history, the working tree is clean,
everything looks finished. The next person to pop that stash gets a conflict
against a change that is already there — or, when the lines coincide, no
conflict and no effect, which is worse.

## Stashing is not a filing system

The stash is good for *minutes*: you need a clean tree to pull, or to look at
another branch, and you want your work back shortly. It is bad for days, and
this exercise is what bad looks like — the entry is unlabelled in `git log`,
invisible in `git status`, attached to no branch, and ordered by a stack index
that moves every time you stash something else.

For anything longer, make a commit on a branch:

```
git switch -c wip/timeouts
git commit -am "wip: timeout handling"
```

A commit has a message, a branch has a name, both show up in every listing, and
`git commit --amend` or `reset --soft` will tidy it up later. The stash's one
advantage — that it does not need a branch — is not worth the invisibility.

## Recovering a stash you dropped

`git stash drop` removes the ref entry and leaves the commit in the database,
so it is recoverable until garbage collection:

```
git fsck --no-reflogs --unreachable | grep commit
git stash store <hash>        # or: git branch rescued <hash>
```

`git stash drop` even prints the hash as it goes:
`Dropped refs/stash@{0} (42dc386...)`. Which is the one good reason to read
command output rather than scroll past it — that line is the only place that
hash appears.

Note the asymmetry this exercise is built on. A dropped stash is a commit, so it
is recoverable. A popped stash you never committed is an *uncommitted edit*, and
there is no reflog for work that was never a commit. `git checkout .` over the
top of it is gone for good.
