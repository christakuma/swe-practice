# Why `revert` and not `reset`

Both get the files back. Only one is safe on a branch other people have pulled.

## What broke

`build.sh` asserts the parser exposes `parse_line`:

```
grep -q "def parse_line" parser.py
```

c3 renamed it to `parse` and did not touch `build.sh`. The diff looked clean in
isolation, which is exactly why it got pushed.

## The two routes, and how they differ

```
git revert --no-edit HEAD        git reset --hard HEAD~1
git push origin main            git push --force origin main

d2261fe c1                      d2261fe c1
2b5faf7 c2                      2b5faf7 c2  <- main, origin/main
42dc386 c3                      (42dc386 reachable only via reflog)
a382308 Revert "c3"  <- main
```

Identical working trees. Wildly different consequences.

`reset --hard` moves the *branch pointer* backwards. c3 is still in your object
store — the reflog knows it — but it is no longer an ancestor of `main`. Once
you force-push that, three things happen to the teammate who already pulled c3:

1. Their `main` and your `main` have diverged with no common tip, so their next
   `git pull` either conflicts or, if they pull with the default merge strategy,
   **silently reintroduces c3** and re-breaks the build.
2. Anyone who branched off c3 is now based on a commit that is not in the
   shared history.
3. Anything pushed to `origin/main` in the window between your `reset` and your
   `push --force` is destroyed without a warning. `--force-with-lease` narrows
   that window; it does not make rewriting published history safe.

`git revert` adds a **new** commit whose diff is the inverse of c3. c3 stays
reachable, history only ever grows, and your teammate's next pull is an
ordinary fast-forward. That is the entire reason it exists.

## Why the push is part of the answer

The exercise fails you for reverting locally and stopping. The build is broken
for *everyone*, and a fix that only exists on your machine has not fixed
anything. `fix-published` checks that `origin/main` actually points at your
revert.

## When rewriting *is* fine

The rule is about *published* history, not about rewriting as such:

- A local branch nobody has fetched — rewrite freely. `rebase -i`, `commit
  --amend`, `reset` are all normal tools.
- Your own feature branch that only you push — force-push is routine, and
  `--force-with-lease` protects you from clobbering your own other machine.
- A shared branch like `main` — add commits, never rewrite.

## The thing worth remembering

Before you change a repository, know where every ref points. `git log --oneline
--decorate --all` and `git status --short --branch` take three seconds and tell
you whether you are about to do something recoverable. The advisory check on
this exercise exists because reading first is the habit that separates a bad
afternoon from an incident.
