# The commits were never gone

`reset --hard` does two things: it moves a branch pointer, and it overwrites
your working tree. It does **not** delete commits. The objects stay in
`.git/objects` until garbage collection runs, and gc will not touch anything
the reflog still references — by default, for 90 days.

So this was never a recovery of lost data. It was a search for a pointer.

## Why `git log` lied to you

`git log` walks *backwards from a ref*. After the reset,
`feature/csv-export` pointed at c1, so `log` had nothing to walk to. The two
commits were still sitting right there, reachable by hash, invisible to every
tool that starts from a branch.

The reflog starts somewhere else: it is an append-only record of every value
`HEAD` has held, in order, regardless of whether anything points at those
values now.

```
57bbe81 HEAD@{0}: checkout: moving from main to feature/csv-export
57bbe81 HEAD@{1}: checkout: moving from feature/csv-export to main
57bbe81 HEAD@{2}: reset: moving to main          <- the mistake
a4eeb2e HEAD@{3}: commit: Add tests for CSV exporter   <- the tip you want
1a8f01f HEAD@{4}: commit: Add CSV exporter
57bbe81 HEAD@{5}: checkout: moving from main to feature/csv-export
57bbe81 HEAD@{6}: commit (initial): Add project skeleton
```

Read the *descriptions*. `HEAD@{1}` and `HEAD@{2}` are the wandering around
you did after the reset — grabbing the top entry, or the second, gets you
nothing. Every branch also keeps its own reflog, so
`git reflog show feature/csv-export` is an equally good route here and is
often quieter.

## The four ways this goes wrong

**Checking the commit out instead of moving the branch.** `git checkout
a4eeb2e` brings the files back and feels like success. But
`feature/csv-export` never moved, and `HEAD` is now detached — so the work
is one careless `git switch` away from being orphaned again, and any commit
you make sits on no branch at all. Recovery means moving the *ref*.

**Rebuilding instead of recovering.** Cherry-picking the range gives you
byte-identical files and brand-new commits:

```
recovered:    a4eeb2e  Add tests for CSV exporter
rebuilt:      c2b9c97  Add tests for CSV exporter    <- different commit
```

Same tree, same message, different hash, rewritten committer date, and the
originals still orphaned. Fine as a last resort; pointless when the real
commits are three keystrokes away.

**Recovering onto the wrong branch.** `reset --hard` obeys whatever branch
you are on. Do it on `main` and you have failed to fix the feature branch
*and* broken one that was healthy.

**Waiting.** The reflog is local, it is not pushed, and it expires. `git gc`
after 90 days (30 for unreachable objects) and this genuinely becomes
unrecoverable. If you have just destroyed work, look now.

## What to reach for, in order

1. `git reflog` — covers everything that moved `HEAD`: resets, checkouts,
   rebases, amends, bad merges.
2. `git reflog show <branch>` — narrower and quieter when you know which
   branch was hurt.
3. `git fsck --lost-found` — for commits the reflog does not cover, such as a
   dropped commit from an interactive rebase or a stash you cleared.
4. `git stash list` — surprisingly often the answer when "my changes vanished"
   turns out to mean an interrupted `git stash`.

## The habit worth building

Before any command that moves a branch pointer or touches the working tree,
know where you are: `git status --short --branch`. And when you are about to
do something you are unsure of, `git branch backup/wip` costs nothing. The
reflog is a safety net, not a plan.
