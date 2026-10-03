# `reset` has three modes, and only the middle word changes

Every `git reset` moves the current branch to the commit you name. What the
three flags choose is how much *else* it takes with it:

| flag | branch | index | working tree |
|---|---|---|---|
| `--soft` | moves | untouched | untouched |
| `--mixed` (default) | moves | reset to the commit | untouched |
| `--hard` | moves | reset to the commit | reset to the commit |

Read that table from the right-hand side. `--hard` is the only one that can
destroy work, because it is the only one that writes to your files. `--soft` is
the safest command in this family and it is the one this exercise needs: the
branch pointer goes back three commits, and the index still holds everything
those commits did — staged, ready to commit once.

```
before                       after reset --soft origin/main

d2261fe c1 <- origin/main    d2261fe c1 <- origin/main, main
2b5faf7 c2 "Add rate limiter"   index: everything c2..c4 changed, staged
42dc386 c3 "fix typo"           worktree: unchanged
a382308 c4 "fix typo again"
           <- main           then commit -> one commit on top
```

## Why not `rebase -i`

Interactive rebase is the answer most people reach for, and for squashing a
*contiguous run of commits at the tip* it does more work for the same result.
`reset --soft` is one command, has no editor step, cannot stop half-finished in a
state you have to `--abort` out of, and the mechanism is visible: you can run
`git status` in the middle and see exactly what you are about to commit.

`rebase -i` earns its keep when the commits are not at the tip, when you want to
reorder them, or when you want to keep some and squash others.

## The ordering that turns this into an incident

The two counter-examples this exercise ships fail different checks and only one
of them is recoverable.

`git reset --hard origin/main` loses the code. Recoverable: the commits are still
in the reflog, so `git reset --hard HEAD@{1}` brings them back, and the whole
window of danger is "until the reflog expires".

`git push` and *then* squash is not recoverable, and it looks fine locally. You
end up with the right two commits and a remote holding four, where the fourth is
no longer an ancestor of yours. Nobody can fast-forward. Every colleague who
pulled gets a divergence they have to resolve by hand, and the only way to clean
up the remote is `push --force`, which is the thing you were trying to avoid.

That is why `still-ahead-of-origin` is a required check and not a nicety. It is
the invariant — *everything origin has is still an ancestor of what I have* —
that separates rewriting your own drafts from rewriting shared history.

## The rule, stated so it transfers

Rewriting history is a local-only operation. The question is never "is this
commit old?" or "did I write it?" — it is **has anything outside my machine seen
it?** `git log --oneline origin/main..HEAD` is the answer: those commits are
yours to reshape however you like, and everything below that line is not.
