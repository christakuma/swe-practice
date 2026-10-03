# Cherry-pick copies a diff; it does not move a commit

`git cherry-pick <rev>` takes the difference between `<rev>` and its parent and
applies it to the branch you are on, as a new commit. The original stays exactly
where it is.

```
main                        release/1.x

c1 ------------------------ c1
c2 "feature flags"             \
c3 "Fix rounding"  ----------> c3* "Fix rounding"
c4 "bulk upload"
```

`c3*` is a different commit from `c3`: different parent, different hash. What it
keeps is the **subject, the body and the author** — and that is the part that
matters six weeks later, when someone asks whether the rounding fix ever shipped
in 1.x.

## Why merging is the wrong tool here

Merging answers "bring me everything from over there". Backporting is the
opposite question: *only* this change. On a release branch that has not moved
since it was cut, the merge is even quieter than usual, because it fast-forwards
— the release branch simply becomes `main`, with no merge commit anywhere to
show in a log that something unusual happened.

That is how an unreviewed feature ships in a patch release. It is also why
`one-commit-added` is a required check: the file contents alone cannot tell you
whether anything extra arrived.

## Why not just retype the change

Because it is three lines and the fix is obvious, retyping is tempting, and it
loses two things:

- **The subject.** `git log --oneline release/1.x` should contain the same
  sentence as `main`. Searching for "rounding" has to find it on both.
- **`git cherry`.** `git cherry main release/1.x` lists every commit on `main`
  that has no equivalent on the release branch, matching by *patch id* — the
  hash of the diff, not of the commit. A cherry-picked commit is recognised as
  already present. A hand-retyped one often is too, if the diff is byte-identical
  — and stops being recognised the moment your retyped version differs by a
  space. That makes the release audit unreliable in exactly the case where you
  most want it.

## Naming the commit without pasting a hash

`main~1` is "the first parent of `main`'s tip". `main^` is the same thing.
`main~2` is two back. Using those instead of a literal hash is worth the habit:
the command still says what you meant if the history moves, and it is readable
in a shell history or a runbook.

The relative forms are also what makes this exercise's reference solution stable
— a pinned hash in a command list breaks the moment the fixture changes, and
says nothing about *which* commit was intended.

## When the cherry-pick conflicts

The release branch is old, so a backport can fail to apply:

```
git cherry-pick main~1
# CONFLICT (content): Merge conflict in billing.py
```

Then it stops, leaves the conflict in your working tree, and waits. Resolve,
`git add`, and `git cherry-pick --continue` — or `git cherry-pick --abort` to
pretend it never happened. The further the release branch is from `main`, the
more likely this is, which is the real argument for backporting promptly rather
than in a batch at the end of the quarter.

## The other direction

Cherry-picking *from* a release branch *into* `main` is the same command and a
worse idea. A fix made on the release branch should land on `main` first and be
backported — otherwise the two histories diverge in content, and the next
release branch you cut from `main` silently loses the fix. The rule people
remember as "fix forward" is this: the fix belongs on the line of development
that everything else is cut from.
