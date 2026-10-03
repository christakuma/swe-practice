# A deleted file is still in the history; the trick is naming where

Deleting a file in git adds a commit that says the file is gone. Every commit
before it still contains the file, in full, so "restoring" it is a copy out of
history rather than a recovery of anything lost.

The three commands that matter are each one step of the same question.

```
git log -- tools/healthcheck.sh                     # which commits touched it
git log --diff-filter=D -- tools/healthcheck.sh     # which one deleted it
git show <that>~1:tools/healthcheck.sh              # what it looked like before
git checkout <that>~1 -- tools/healthcheck.sh       # put it back
```

`--diff-filter` takes a letter per change type: `A` added, `M` modified, `D`
deleted, `R` renamed. `D` is the one that answers "when did this vanish",
and it is worth knowing because the alternative is reading every commit that
touched the path.

## The off-by-one that matters

The commit that deletes a file **does not contain it**. So the revision you want
is that commit's *parent* — `<rev>~1`, or `<rev>^`, which is the same thing.

```
git show main~2 --stat        # the deletion: healthcheck.sh | 5 -----
git show main~3:tools/healthcheck.sh    # the file, intact
```

Getting this wrong produces a confusing error rather than a wrong answer:
`fatal: path 'tools/healthcheck.sh' does not exist in 'main~2'`. Which is git
telling you precisely what happened, if you read it.

## `checkout --` versus `restore --source`

```
git checkout main~3 -- tools/healthcheck.sh
git restore --source=main~3 -- tools/healthcheck.sh
```

Identical effect: write that version of the path into the working tree and the
index. `git restore` is the newer command and the better one to learn, for the
reason `git switch` is better than `git checkout <branch>` — `checkout` does two
unrelated jobs and picks between them by guessing from its arguments, which is
how `git checkout main` and `git checkout -- main` end up meaning entirely
different things.

The `--` matters in both. It separates revisions from paths, and without it git
has to guess whether `main` is a branch or a file. When a branch and a file share
a name, the guess is wrong.

## Why not just reset back to before the deletion

```
git reset --hard main~3
```

This restores the file perfectly. It also discards the three commits made since
— the README change, the rollback script — because the branch pointer has moved
behind them. On an unpushed branch that is recoverable from the reflog; on a
published one it is a rewrite of shared history.

The shape to notice: a check on the *file* cannot tell this answer apart from the
right one. Only a check on the *history* can, which is why `history-only-grew`
and `one-commit-added` are both required here. It is the same lesson as
[`git/revert-a-pushed-commit`](../revert-a-pushed-commit/notes.md), arriving from
the other direction.

## Restoring a file that was renamed rather than deleted

```
git log --follow -- tools/healthcheck.sh
```

`--follow` keeps tracking a path across renames, which plain `git log -- <path>`
does not. If `--diff-filter=D` finds a deletion that looks like it should have
been a rename, the file is probably still in the tree under another name, and
`git show <rev> --stat` on the "deleting" commit will show both halves.
