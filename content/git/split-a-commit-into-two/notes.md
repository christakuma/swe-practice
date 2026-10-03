# The index is the feature; `reset` just gets you back to it

Most people meet the staging area as an annoyance — an extra `git add` between
editing and committing. This exercise is the case it exists for: the working
tree holds two unrelated changes, and the index is what lets you commit one of
them.

```
git reset HEAD~1        # branch back one, index back one, files untouched
git add convert.py      # stage only the fix
git commit -m "..."     # commit only what is staged
git add CHANGELOG.md
git commit -m "..."
```

Nothing clever happens. The only git-specific step is the first one, and it is
the default mode of `reset`:

| mode | branch | index | working tree |
|---|---|---|---|
| `--soft` | moves | untouched | untouched |
| `--mixed` (default) | moves | reset | untouched |
| `--hard` | moves | reset | reset |

`--mixed` is what you want here and `--soft` is what you want for
[squashing](../squash-fixups-before-pushing/notes.md). The difference is one
word and it is the whole difference between "give me these changes back to
re-stage" and "give me these changes back already staged".

## Why the order of the two commits matters

The final tree is identical either way, so the order looks cosmetic. It is not,
because a commit is the unit of almost every operation you will later want:

- **`git revert`** — reverting the fix should not revert a changelog entry, and
  vice versa
- **`git cherry-pick`** — backporting the fix to a release branch should not
  drag documentation changes along with it
- **`git bisect`** — a bisect that lands on a commit which edits only markdown
  has told you nothing, and you have spent a step of a binary search on it
- **`git log -- convert.py`** and **`git blame`** — a commit whose subject
  mentions two things is a commit whose subject describes neither

That is why `fix-came-first` is required rather than advisory. "One commit, one
idea" is not tidiness; it is what makes the history queryable.

## Staging part of a *file*

This exercise splits by file, which is the easy case. When the two changes are
in the same file:

```
git add -p convert.py
```

...walks you through each hunk: `y` to stage it, `n` to skip, `s` to split the
hunk smaller, `e` to edit the staged version by hand. That is the general tool,
and `git diff --staged` before committing is how you check you got it right.

The trap with `-p` is that the *working tree* still holds everything, so your
first commit contains a version of the file that may never have been tested.
`git stash --keep-index` is the manoeuvre for that: stash everything that is not
staged, run the tests on what you are about to commit, commit, then `git stash
pop`.

## Splitting a commit that is not the tip

`reset HEAD~1` only reaches the last commit. For one further back, the
mechanism is `git rebase -i <before it>`, mark that commit `edit`, and when the
rebase stops you are sitting on it with the tip reset — at which point this
exercise's answer applies, followed by `git rebase --continue`.

Same shape, one more layer. And the same precondition: every commit involved
has to be unpushed, because all of this replaces commits rather than adding
them.

## The answer that looks like it worked

```
git reset HEAD~1
git add -A
git commit -m "Fix offset sign and start a changelog"
```

Two commands in and one command out, a clean `git status`, identical files — and
a history with exactly the commit you were trying to split, under a new hash.
`git log --oneline` looks right if you are not counting. The `two-commits-now`
check is a commit count for precisely this reason: nothing about the content can
tell you whether the split happened.
