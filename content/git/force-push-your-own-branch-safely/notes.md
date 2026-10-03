# The lease is the difference between forcing and overwriting

```
git push --force                  # make the remote match me. No questions.
git push --force-with-lease       # ... but only if the remote is where I last saw it.
```

`--force-with-lease` compares the remote's current value against your
remote-tracking ref — the value from your last fetch. If they match, nobody has
pushed since you looked, and the force is safe. If they do not:

```
 ! [rejected]  feature/search-ui -> feature/search-ui (stale info)
```

That is not a failure. That is the only mechanism in git that will tell you
somebody else has pushed to a branch you were about to rewrite. Plain `--force`
makes no check, prints nothing unusual, and succeeds.

**Use `--force-with-lease` every time you would have used `--force`.** There is
no situation where you preferred the unchecked version; there is only not having
heard of the checked one.

## The two rejections say different things

```
! [rejected]  (non-fast-forward)   # you rewrote history; expected
! [rejected]  (stale info)         # someone pushed; not expected
```

The first is the normal consequence of a rebase, an amend or a squash: the
remote cannot fast-forward onto a branch whose commits have new hashes. You
answer it with a force-push.

The second is the lease refusing. You answer it by **fetching and finding out
what happened** — never by escalating to `--force`, which is answering "someone
else has work here" with "not any more".

## Why their commit cannot be kept as their commit

This is the part worth sitting with. The colleague's test was committed on top of
`s1` and `s2`. You squashed those two commits into one, so `s1` and `s2` no
longer exist in your branch — and a commit is defined partly by its parent, so
there is nowhere for theirs to attach.

```
origin had:   c2 - s1 - s2 - r1
you have:     c2 - s12
```

Rebasing `r1` onto `s12` would work if `r1`'s content did not overlap the
squashed commits; here it does not, so `git cherry-pick origin/feature/search-ui`
is the clean route. Either way the result is a **new commit with a new hash**.
Their authorship survives; the commit identity does not.

That is a genuine, unavoidable cost of rewriting a branch somebody else has
pushed to, and the reason the rule is what it is: rewrite only history that is
yours alone. "Yours alone" means nobody has pushed to it *and* nobody has pulled
it — and a branch you opened a review on is a branch someone may have done
either to.

## The retreat, and when it is right

```
git fetch origin
git reset --hard origin/feature/search-ui
```

Abandon your rewrite, take what the remote has, redo the tidy-up later or not at
all. This exercise grades it as a wrong answer because the task was to publish
the squash — but in a real emergency, at the end of a long day, on a branch three
people are working on, it is the right instinct. Nothing is lost and nothing is
risked.

The question it turns on is the same one the whole track asks: how many other
people's copies of this history exist? One is enough for a force-push to be
somebody else's problem.
