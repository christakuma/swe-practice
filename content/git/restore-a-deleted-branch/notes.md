# `git branch -D` deletes forty-one bytes

A branch is a file in `.git/refs/heads/` containing a commit hash. Deleting the
branch deletes that file. The commits are untouched — they are still in
`.git/objects`, byte for byte, and `git cat-file -p <hash>` will print them.

What you lose is *reachability*. `git log`, `git branch` and `git status` all
answer questions about commits reachable from a ref, so a commit nothing points
at is invisible to every one of them. That is the whole of the problem, and it is
why the recovery is a pointer operation rather than anything that touches files.

```
after git branch -D feature/webhooks

c1 ---- c2  <- main
  \
   w1 -- w2   (reachable from nothing; still in the object store)
```

## Why `-D` and not `-d`

`git branch -d` refuses to delete a branch whose commits are not merged
anywhere:

```
error: the branch 'feature/webhooks' is not fully merged
```

That is the guard rail, and `-D` is the override. People learn `-D` early because
`-d` said no once, and then use it by default — which turns a guard rail into a
keystroke. If `-d` complains, the correct response is to read what it said, not
to capitalise the flag.

## Reading the reflog rather than counting it

`git reflog` lists every position `HEAD` has held:

```
a382308 HEAD@{0}: commit: Document where deploys come from
d2261fe HEAD@{1}: checkout: moving from feature/webhooks to main
42dc386 HEAD@{2}: commit: Retry failed webhook deliveries
2b5faf7 HEAD@{3}: commit: Add webhook delivery
d2261fe HEAD@{4}: checkout: moving from main to feature/webhooks
d2261fe HEAD@{5}: commit (initial): Add project skeleton
```

Each line records the value `HEAD` *became*. The entry you want here is
`HEAD@{2}` — the last commit made while you were on the branch. `HEAD@{3}` is
the first of the two, and restoring to it is this exercise's second
counter-example: the branch comes back one commit short and the log looks
plausible.

`git show --stat HEAD@{2}` before acting is the habit. Indices shift every time
anything moves `HEAD`, so a number you worked out three commands ago may not mean
what it did.

Note what the deletion *did* take: the branch's own reflog, at
`.git/logs/refs/heads/feature/webhooks`. That is why this recovery goes through
`HEAD`'s reflog instead — `git reflog feature/webhooks` has nothing left to
read.

## The other two routes

```
git fsck --lost-found
```

Reports every unreferenced object in the repository — "dangling commit
42dc386…". It is the tool when there is no reflog entry either: a clone that
never had the branch, a `.git/logs` that was cleaned, a commit orphaned by a
rebase in a repository you have since re-cloned. It is noisier, it cannot tell
you which dangling commit you meant, and it works when nothing else does.

```
git branch feature/webhooks <hash from the reflog>
```

Any revision works as `git branch`'s second argument: a hash, `HEAD@{2}`, a tag,
another branch. There is no special "undelete" command because there does not
need to be one.

## How long you have

Unreferenced commits survive until they are garbage collected, and the defaults
are generous:

| setting | default | what it expires |
|---|---|---|
| `gc.reflogExpire` | 90 days | reflog entries for commits still reachable |
| `gc.reflogExpireUnreachable` | 30 days | reflog entries for commits that are not |
| `gc.pruneExpire` | 2 weeks | loose objects nothing refers to at all |

`git gc` runs automatically once enough loose objects accumulate, so the clock
starts when you delete the branch rather than when you next type a command.

So: weeks, not minutes. But the honest version of the rule is that the window
exists and you should not plan around its size. This practice environment pins
`gc.auto = 0` and both reflog expiries to `never`, precisely so that an exercise
about recovering unreferenced commits cannot become unsolvable while you are
reading the hints.
