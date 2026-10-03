# A conflict is git refusing to guess

Git merges by comparing both sides against their common ancestor. Where only
one side changed a region, it takes that change. Where both changed the same
region differently, it has no rule that could be right — so it stops, writes
both versions into the file, and marks the path unmerged.

```
[server]
host = 0.0.0.0
port = 8080
<<<<<<< HEAD
workers = 4
timeout_seconds = 30
=======
workers = 8
>>>>>>> feature/tune
```

- above `=======` is **HEAD**: the branch you are on, `main`
- below it is the branch being merged in
- the lines outside the markers merged cleanly and are already correct

Note what got pulled into the conflict: `timeout_seconds = 30` was not in
dispute. Nothing on the other side touched it. It is inside the block because it
is *adjacent* to the line that was in dispute, and git's unit of conflict is a
region of lines, not a line. That is why one-sided resolutions lose things
nobody was arguing about.

## The three states of a conflicted file

```
git status --short
UU settings.ini      # both sides modified it
```

The index holds three entries for that path — the ancestor, ours, theirs —
which is what `git checkout --ours` and `--theirs` read. Staging the file
collapses them to one:

```
git add settings.ini     # "resolved"
git status --short
M  settings.ini
```

`git add` is a claim, not a check. Git does not read the file to see whether you
removed the markers, which is how `<<<<<<<` ends up in production config. The
only safety net is the one this exercise models: look at the file after you
think you are done.

## `--ours`, `--theirs`, and when they are fine

```
git checkout --ours settings.ini     # discard their version of this file
git checkout --theirs settings.ini   # discard ours
```

Both are whole-file operations, and both are legitimate when one side is
*known* to be right — a generated file, a lockfile you are about to regenerate,
a change you have already decided to abandon. They are the wrong reflex when the
conflict is a disagreement about content, because they resolve it by not reading
it.

The naming is also a trap worth knowing: during a **rebase**, "ours" and
"theirs" are swapped relative to what you expect, because a rebase replays your
commits onto the upstream — so the upstream is "ours" and the commit being
replayed is "theirs". That is covered in
[`git/resolve-a-conflict-during-a-rebase`](../resolve-a-conflict-during-a-rebase/notes.md).

## Finishing, and getting out

```
git add <each resolved path>
git commit --no-edit        # accept the prepared merge message
```

`git commit` refuses while any path is unmerged, which is the one guard rail
here. `--no-edit` takes the message git prepared (`Merge branch
'feature/tune'`); without it, git opens an editor — and in this sandbox the
editor is pinned to `false`, so the commit fails immediately rather than hanging.

And the escape hatch:

```
git merge --abort
```

Puts everything back exactly as it was before the merge, at any point before you
commit. It is the reason a conflict is never an emergency: you can always stop,
read, and start again.

## The thing worth remembering

`git merge` exiting 1 is not an error to be undone. It is the one moment in a
merge where a human is required, and the file in front of you contains both
intentions and no decision. Read both sides before you touch it — the cost of
getting this wrong is not a broken build, it is a change that silently went
missing and will be noticed in a month.
