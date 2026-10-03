# A branch is a file containing a hash

`.git/refs/heads/main` is forty-one bytes: a commit hash and a newline. That is
the entire implementation of a branch, and once you believe it, this exercise
stops being about moving commits — commits never move — and becomes about which
of two pointers you are editing.

```
before                            after

d2261fe c1 <- origin/main         d2261fe c1 <- origin/main, main
2b5faf7 c2                        2b5faf7 c2
42dc386 c3 <- main (HEAD)         42dc386 c3 <- feature/export
```

Nothing was copied. The same three commits are there in both pictures. One new
pointer appeared and one existing pointer moved.

## Why the order is forced

`git branch feature/export` names *the current commit*. So it has to happen
while `main` is still at c3 — after the reset, the current commit is c1 and
`git branch feature/export` gives you a branch at the skeleton, which is the
counter-example this exercise ships.

The commits are not gone at that point. `git reset --hard` leaves them in the
object store and leaves the position in the reflog, so the recovery is
`git branch feature/export <sha from the reflog>`. But you have gone from a
two-command answer to one that requires finding something, and the whole reason
to learn the order is to not need the reflog.

## The other version of this mistake

```
git checkout -b feature/export      # switches to the new branch
git reset --hard origin/main        # ... and resets THAT branch
```

Both branches end up at the skeleton commit. The commands are individually
right, and `-b` quietly changed which branch the second one applies to. This is
why `git status --short --branch` is worth the keystroke before any `reset`: it
prints the branch you are about to move.

`git switch -c` and `git checkout -b` behave identically here. `git switch` is
the newer, narrower command — it only changes branches, where `checkout` also
restores files — and `git restore` is the other half. Worth preferring them for
exactly that reason: `checkout` is one command for two unrelated jobs, and which
one it does depends on the arguments.

## Why `--hard` is safe in this answer

`reset --hard` is the dangerous mode: it writes your files. It is safe *here*
because the working tree is already clean and the commits it winds past are
reachable from `feature/export`, which you just created. Both halves of that
sentence matter, and the first is the one people forget — `--hard` with
uncommitted changes destroys them with no reflog entry to recover from, because
they were never committed.

If the worktree had been dirty, the answer would have been `git stash`, the two
pointer moves, then `git stash pop` on the branch where the changes belong.

## When this comes up for real

Almost always as: *I have been working for an hour and just realised I am on
`main`.* The fix is this exercise, and it gets easier the sooner you notice,
because `origin/main` is the thing you reset back to and someone else may have
moved it since. If `main` has already been pushed, this is no longer the answer
at all — the work is published, and the tool for that is `git revert`, or simply
leaving it alone.
