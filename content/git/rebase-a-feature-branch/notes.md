# Rebase moves the branch you are standing on

That one sentence is most of what goes wrong with rebase. The command reads like
an instruction about its argument — `git rebase main` sounds like it does
something to `main` — and it is the opposite: the argument is the **destination**,
and the thing that moves is `HEAD`'s branch.

```
before                          after git rebase main
                                (standing on feature/report)

c1                              c1
c2 ----.                        c2
|      f1                       m1  <- main
m1     f2  <- feature/report    f1* 
<- main                         f2* <- feature/report
```

`f1` and `f2` are gone and `f1*` and `f2*` are new commits with new hashes. A
rebase does not move commits; it re-creates them, one at a time, with a different
parent. Which is why it is a history rewrite and why it is only safe on a branch
nobody else has.

## Merge or rebase

Both get `main`'s work into your branch. They are answering different questions.

```
merge main into feature             rebase feature onto main

c1                                  c1
c2 ----.                            c2
|      f1                           m1
m1     f2                           f1*
|      |                            f2*
'------M  <- feature/report         <- feature/report
```

- **Merge** is honest about what happened: two lines of work existed and were
  joined at a point in time. It never rewrites anything, so it is the only
  option for a shared branch.
- **Rebase** produces the history you *wish* had happened: a straight line, each
  commit standing on current code. It rewrites, so it is only available while the
  branch is yours alone.

The usual house rule follows from that and not from taste: **rebase your own
branches, merge shared ones.** `main` gets merges; a feature branch nobody has
fetched gets rebased.

What the merge costs in practice is not the picture. It is that `git log` of the
feature branch now interleaves someone else's commits with yours by date, and
that a reviewer reading commit-by-commit sees a commit nobody ever wrote: the
merge, whose diff is "everything that happened on main", attributed to you.

## The mistake this exercise ships as a counter-example

```
git rebase feature/report      # standing on main
```

This is the command people type when they mean the other one, because it names
the branch they are thinking about. It replays `main`'s commits onto
`feature/report`, which rewrites `main` — a published branch. Locally everything
looks tidy. The next `git push` is rejected as non-fast-forward, and that
rejection is the first sign anything is wrong.

`git status --short --branch` before any rebase prints the branch that is about
to be rewritten. It is the cheapest habit in this whole track.

## What a conflict does to the picture

This exercise cannot conflict — the two sides touch different files. When one
does:

1. The rebase stops partway, HEAD detached, the conflicted files in your working
   tree with markers in them.
2. You resolve, `git add` the files, and `git rebase --continue`.
3. Repeat per commit. A rebase of five commits can stop five times, and it can
   stop on the *same* conflict more than once, because each commit is replayed
   against the result of the last.
4. `git rebase --abort` at any point puts everything back exactly as it was.

That `--abort` is the reason rebase is less frightening than it looks: until it
finishes, it is fully reversible. And `ORIG_HEAD` covers you after it finishes —
`git reset --hard ORIG_HEAD` undoes a completed rebase, which is what
[`git/undo-a-rebase-with-orig-head`](../undo-a-rebase-with-orig-head/notes.md) is
about.

## `--force-with-lease`, if the branch was pushed

A rebased branch cannot be pushed normally — its commits have new hashes, so the
push is not a fast-forward. For your own branch that is fine and routine:

```
git push --force-with-lease
```

The lease means "refuse if the remote has moved since I last fetched", which
protects you from clobbering a push from your other machine. Plain `--force`
does not ask. Use the lease version always; there is no case where you wanted
the other one.
