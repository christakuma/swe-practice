# Reverting a merge needs you to say which side was the mainline

```
git revert HEAD
error: commit a382308 is a merge but no -m option was given.
fatal: revert failed
```

Git is not being awkward. Reverting a commit means applying the inverse of its
diff, and a merge commit has two parents — so it has two diffs, one against each
side, and "the inverse" is undefined until you pick one.

```
      c2
     /  \
   d1    |
   d2    |
     \  /
       M   <- main, origin/main
```

`-m 1` means "the first parent is the line of history I am keeping", so undo
everything the *other* parent brought in. For a merge made while standing on
`main`, the first parent is `main`. That is the one you want almost always, and
`git log --format=%p` on the merge will show you both parents in order if you
want to be sure.

```
git revert --no-edit -m 1 HEAD
```

## Why not reset past it

```
git reset --hard HEAD~1
git push --force origin main
```

Same files, tidier history, and it rewrites a merge that is already on
`origin`. Everyone who pulled has the merge; after the force-push their `main`
and the remote's have diverged with no common tip, and two commits of the
colleague's branch are no longer in the shared history. The symmetric case is
in [`git/revert-a-pushed-commit`](../revert-a-pushed-commit/notes.md); the rule
is the same and the blast radius here is larger, because a merge is what other
people's branches get rebased onto.

## The consequence nobody mentions until it bites

Reverting a merge leaves the merge in history. So git still believes the
branch's commits are incorporated:

```
git merge feature/discounts
Already up to date.
```

Which is literally true — `d1` and `d2` are ancestors of `main` — and
completely useless, because their *content* was undone by the revert. This is
the single most surprising thing about reverting merges, and it has two
standard answers:

1. **Revert the revert.** `git revert <the revert commit>` brings the content
   back, and then new work on the branch merges normally on top. Ugly in the
   log, correct, and the one to use when the feature is coming back roughly as
   it was.
2. **Rebuild the branch.** Rebase `feature/discounts` onto the current `main`,
   which gives its commits new hashes that `main` has never seen, so the merge
   is a real merge again. Cleaner history, available because the branch is not
   shared.

Either way, decide before you revert, and say which in the revert's commit
message. A team that hits this cold usually concludes the feature was merged
and then cannot find it.

## When it conflicts

Reverting a merge can conflict, because the inverse diff is being applied to a
`main` that has moved on since. It stops the same way a merge does — files
staged, commit unmade — and finishes with `git revert --continue` or
`git revert --abort`. The `clean-worktree` check here is what catches stopping
halfway: the content is right and nothing has been committed.
