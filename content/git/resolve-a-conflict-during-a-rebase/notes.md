# A rebase is a loop, and it stops once per commit that will not apply

`git rebase main` on a two-commit branch does this:

```
checkout main
apply f1   -> conflict, stop
             (you resolve, commit, --continue)
apply f2   -> clean
reattach feature/backoff to the last commit
```

While it is running you are on a detached HEAD part-way through the list. That
is normal and temporary, and it is why `rebase-finished` is a required check
here: a rebase that is still waiting for you looks, from the outside, almost
exactly like one that is done.

## Finishing a stop

```
git status --short          # UU retry.py
write retry.py ...          # the file you want
git add retry.py            # "resolved"
git commit --no-edit        # keep f1's original message
git rebase --continue       # on to f2
```

`git commit --no-edit` is worth knowing in this sandbox and out of it: `git
rebase --continue` on its own opens an editor for the commit message, and
committing first with `--no-edit` reuses the message git already prepared. Then
`--continue` has nothing to commit and simply proceeds.

Three ways out, and they are not equivalent:

| command | what it does |
|---|---|
| `git rebase --continue` | you resolved it; carry on |
| `git rebase --skip` | **drop the commit being applied** and carry on |
| `git rebase --abort` | undo the whole rebase, back to where you started |

`--skip` is the dangerous one. It is for a commit that has become genuinely
redundant — already applied upstream, say — and when reached for as "make this
conflict go away" it silently deletes a commit's worth of work. The rebase then
reports success. In this exercise it drops the backoff function and the attempt
count together, and leaves the jitter commit calling a function that no longer
exists.

`--abort` is always available until the rebase finishes, and after it finishes
`git reset --hard ORIG_HEAD` undoes the whole thing — see
[`git/undo-a-rebase-with-orig-head`](../undo-a-rebase-with-orig-head/notes.md).
Between those two, a rebase is reversible at every moment, which is the fact
that makes it worth using at all.

## `--ours` and `--theirs` are swapped during a rebase

This is the one piece of git vocabulary that is genuinely counter-intuitive, and
the reason is mechanical. A rebase checks out the **upstream** and replays your
commits onto it. So at the moment of the conflict:

- `--ours` is `main` — the branch you are rebasing *onto*, which is checked out
- `--theirs` is the commit being applied — **your own commit**

The opposite of a merge, where `--ours` is the branch you are on and `--theirs`
is the one coming in. Same two words, different referents, and no warning when
you get it wrong — you get a clean resolution that silently kept the wrong side.

`git checkout --conflict=diff3 <path>` is the defence: it rewrites the conflict
with a third section showing the common ancestor, so you can see what each side
actually changed rather than inferring it from which block is on top.

## Conflicting more than once

A five-commit rebase can stop five times, and it can stop on the *same lines*
repeatedly, because each commit is replayed against the result of the last. That
is the real cost of rebasing a long-lived branch, and it is what
`git rerere` exists for: enable `rerere.enabled` and git records each
resolution, replaying it automatically the next time the same conflict appears.

The cheaper fix is not to have long-lived branches. A branch rebased daily
conflicts in small, recognisable ways; one rebased after three weeks conflicts
in ways that need the original author.
