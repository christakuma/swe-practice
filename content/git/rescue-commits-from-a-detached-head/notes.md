# Detached HEAD means `HEAD` holds a hash instead of a branch name

Normally `.git/HEAD` contains `ref: refs/heads/main`. Detached, it contains a
commit hash directly. Everything still works — you can edit, stage, commit — and
each commit updates `HEAD` to the new hash. Nothing else points at any of them.

```
c1 -- c2  <- main (HEAD after the checkout back)
        \
         d1 -- d2     (reachable from nothing)
```

Which is why `git log --oneline --all` does not show them. `--all` means "from
every ref", and there is no ref.

## Git does warn you

```
Warning: you are leaving 2 commits behind, not connected to
any of your branches:

  42dc386 Evict the least recently used entry
  2b5faf7 Add a bounded cache

If you want to keep them by creating a new branch, this may be a good time
to do so with:

 git branch <new-branch-name> 42dc386
```

That message contains the entire answer, including the hash. It is also printed
at the exact moment you are thinking about something else, which is why this
exercise exists — and why the recovery route through the reflog is worth knowing
even though the warning already told you.

## Why `git branch <name> <rev>` and not a cherry-pick

```
git branch feature/cache HEAD@{1}     # the commits get a name
git checkout -b feature/cache         # a new branch here; commits still orphaned
git cherry-pick ...                   # copies of the commits; originals orphaned
```

All three leave you with a working cache. Only the first one keeps the commits
you actually wrote, with their hashes, their parents and their original
authorship.

The two wrong answers are instructive precisely because they fail the same pair
of checks for opposite reasons: one has the branch and not the work, the other
has the work and not the commits. A check on file contents cannot tell either of
them from the right answer.

## When a detached HEAD is the right place to be

It is not an error state. It is what you want whenever you need a commit checked
out and are not going to build on it:

- `git bisect` detaches at each step, by design
- `git checkout v1.4.0` to look at a tag, or `git checkout <sha>` to reproduce a
  bug from a report
- a CI job checking out a commit rather than a branch — which is why `git branch
  --show-current` is empty in most pipelines

The rule is simply: do not *commit* there unless you mean to. And if you do,
name it before you leave.

## The small habit that prevents it

`git status` says so on the first line:

```
HEAD detached at 2b5faf7
```

A shell prompt that shows the branch shows this too, usually as a bare hash
where the branch name goes. That is the signal to notice before typing
`git commit`, and it is cheaper than the reflog.
