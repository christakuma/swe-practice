# `rebase --onto` exists because "where my work starts" and "where it should go" are different questions

Plain `git rebase <upstream>` uses one argument for both: it replays
`<upstream>..HEAD` onto `<upstream>`. That is right when the only thing between
you and the upstream is your own work. Here it is not.

```
your branch:   c2 - k1 - k2 - y1      <- feature/webhooks
the remote:    c2 - kr1               <- origin/feature/webhooks
```

`git log origin/feature/webhooks..HEAD` lists three commits — `k1`, `k2` and
`y1` — and two of them are *theirs*, in the old form their squash replaced. A
plain rebase would replay all three onto `kr1`, re-applying their work on top of
their own squash of it.

The three-argument form separates the two questions:

```
git rebase --onto <new base> <upstream> [branch]
                  ^ where it goes   ^ what my work starts after
```

```
git rebase --onto origin/feature/webhooks HEAD~1
```

`HEAD~1` is `k2`, so `HEAD~1..HEAD` is exactly `y1`. That one commit is replayed
onto their tip:

```
c2 - kr1 - y1*    <- feature/webhooks
```

And the push is a fast-forward, because their tip is still in there.

## Why not merge

```
git merge origin/feature/webhooks
```

This resolves cleanly and produces the right files, because applying a change
that is already present is usually a no-op. The branch then contains `k1`, `k2`
*and* `kr1` — both versions of their work — joined by a merge commit. Pushing
it puts the two commits they deliberately removed back on the remote.

So the files are right, the tests pass, and the history is the opposite of what
the colleague asked for. That is the hardest kind of wrong answer to notice,
and the reason `replaced-commits-are-gone` is phrased as a negated
`is_ancestor` rather than as anything about content.

## Why not reset

```
git reset --hard origin/feature/webhooks
```

The divergence disappears, your branch matches the remote, and your signing
commit is reachable only from the reflog. Nothing afterwards mentions it:
`git status` is clean, `git log` is tidy, and the work is gone unless you
remember it existed.

It is recoverable — `git reset --hard ORIG_HEAD`, or the reflog — which is worth
knowing, because this is a common panic reaction to a divergence you do not
understand.

## What `--onto` needs you to know

The `<upstream>` argument is the thing people get wrong, because it is not "the
branch I am rebasing" — it is **the last commit I do not want replayed**. Ways
to name it:

- `HEAD~1` when you know how many commits are yours
- the old base by hash, from `git reflog` or from `git merge-base`
- `origin/feature/webhooks@{1}` — the previous value of the remote-tracking
  ref, which is where their branch was *before* the force-push, and therefore
  exactly the commit your work was built on

That last one is the elegant version and is worth knowing: remote-tracking refs
have reflogs too, so `@{1}` is "where this was last time I fetched".

## The cheaper lesson

This situation exists because someone force-pushed a branch other people had.
Everything above is recovery from a decision that should not have been made:
`--force-with-lease` would have refused it if they had not fetched, and nothing
would have refused it if they had. See
[`git/force-push-your-own-branch-safely`](../force-push-your-own-branch-safely/notes.md)
for the other end of this exchange — the two exercises are the same incident
from the two machines involved.
