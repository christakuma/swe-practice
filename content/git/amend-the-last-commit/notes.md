# Amend rewrites, and that is both the point and the risk

`git commit --amend` does not edit a commit. Commits are immutable — the hash is
a hash *of* the tree, the message, the parent and the dates, so changing any of
them produces a different commit. What amend actually does is build a new commit
from the current index with the same parent as the tip, then move the branch onto
it. The old commit is left unreferenced.

```
before                          after

d2261fe c1                      d2261fe c1
2b5faf7 c2  <- origin/main      2b5faf7 c2  <- origin/main
42dc386 c3 "WIP median" <- main a382308 c3* "Add median"  <- main
                                (42dc386 reachable only via the reflog)
```

That is why the two halves of this exercise are one command and not two: the
message and the tree are both inputs to the new commit, so staging the fixed file
before amending changes both at once.

## The failure mode worth internalising

`git commit --amend -m "..."` with nothing staged succeeds. It rewrites the
message and leaves the code exactly as it was. That is a legitimate thing to
want, and it is also what happens when you forget `git add` — and the output is
identical in both cases:

```
[main a382308] Add median
 1 file changed, 10 insertions(+)
```

`1 file changed` describes the commit as a whole, not what you just staged. So
`git show HEAD` afterwards is the three-second check, and `debug-line-gone` reads
the committed blob rather than the working tree for the same reason.

## Why `origin/main` is in this exercise at all

Nothing in the task asks you to push, and one of the required checks is about
`origin/main` anyway. It is there because "is this commit published?" is the only
question that decides whether amend is the right tool, and an exercise that never
made you ask it would be teaching the command without its precondition.

The three states, and what each allows:

| where the commit is | amend? | force-push needed |
|---|---|---|
| your machine only | yes, routinely | no |
| your own branch on origin, nobody else fetches it | yes | yes, `--force-with-lease` |
| a shared branch others have pulled | no — use `git revert` | never do it |

The middle row is the one people get wrong in both directions. It is normal and
safe, and it still needs the lease, because your other laptop counts as someone
else.

## What amend does not fix

The amended commit is a *new* commit, so anything that referred to the old one
now refers to a commit no branch contains:

- a tag already placed on it stays on the old commit
- another branch pointing at it keeps pointing at it
- the hash in a code review or a ticket resolves to something unreachable from
  any branch

None of that argues against amending an unpublished tip. It is the reason the
blast radius grows the moment anything else points at the commit.

## When to reach for which

- tip commit, unpublished, wrong message or missing change → `--amend`
- tip commit, published → `git revert`, or a follow-up commit
- a commit further back, unpublished → `git rebase -i`, or `reset --soft` and
  rebuild
- a commit further back, published → `git revert`

The habit the advisory check rewards is the one that chooses between those: read
`git log --oneline --decorate --all` first, because where your commit sits
relative to `origin/main` decides the answer.
