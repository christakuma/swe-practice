# A rejected push is the remote telling you it has something you do not

```
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs to '/.../origin.git'
hint: Updates were rejected because the remote contains work that you do
hint: not have locally.
```

That is not a permissions problem or a flake. It is the one safety check git
performs on your behalf: a push is only allowed to **fast-forward** the remote
branch — to move it to a commit that has the old one as an ancestor. Your main
and theirs have diverged, so no such move exists.

Everything after that is about how you want the two lines of work joined.

## `origin/main` is a cache, not the remote

`refs/remotes/origin/main` is a local file recording where `origin/main` was the
last time you fetched. In this exercise it says c2 and the remote says r1, so
`git log --decorate --all` shows you a picture that was true yesterday.

```
git fetch origin      # update the remote-tracking refs. Changes nothing else.
```

`git fetch` is the safest command in git: it writes only to `refs/remotes/*`,
never to your branches, your index or your files. There is no state in which
running it makes anything worse, which is why it belongs before any reasoning
about a remote.

## merge, rebase, or reset

Three ways to make the push succeed, and they are not equivalent.

```
git pull                       # fetch + merge: a merge commit joins the two
git pull --rebase              # fetch + rebase: your commit replays on top
git reset --hard origin/main   # discard your side entirely
```

```
merge                      rebase

c2                         c2
|  \                       r1   (theirs)
r1  m1                     m1*  (yours, replayed)
|  /                       <- main
M   <- main
```

- **merge** never rewrites anything, so it is the only safe option when your
  side has already been pushed. The cost is a commit per integration, and on a
  branch with five people that is five merge commits a day whose content is
  "two people worked at the same time".
- **rebase** rewrites *your* unpushed commit and leaves theirs untouched. That
  is what makes it safe here: the commits being rewritten are the ones nobody
  else has. The result is a history someone can read top to bottom.
- **reset --hard** makes the rejection go away by throwing your work out. It is
  on the list because it is short, it works, and people type it.

The rule that follows: **rebase when the only commits being replayed are your
own unpushed ones.** The moment your side has been pushed, merge.

`git config pull.rebase true` makes `git pull` do the right thing by default,
and is one of the few global settings worth turning on everywhere.

## Why `--force` is the wrong button

```
git push --force origin main
```

This succeeds. It sets `origin/main` to your commit, and the colleague's
validation commit becomes reachable from nothing on the remote. No warning is
printed to you, and none to them. The failure surfaces later as either a
confusing pull on their machine or a bug report about bad rows getting imported
— neither of which looks like a git problem.

`--force-with-lease` would have refused: it says "only if `origin/main` is still
where I last saw it", and it was not. That is the whole reason to prefer it, and
it is covered in
[`git/force-push-your-own-branch-safely`](../force-push-your-own-branch-safely/notes.md).

The habit worth having is simpler than any flag: on a shared branch, a rejected
push is never fixed by forcing. It is fixed by integrating.
