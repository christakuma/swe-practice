# An upstream is a piece of local configuration, not a push

Publishing a branch and *tracking* it are two different things, and the second
one is a line in `.git/config`:

```
[branch "feature/csv-upload"]
    remote = origin
    merge = refs/heads/feature/csv-upload
```

`git push -u origin feature/csv-upload` does both: it sends the commits, and it
writes those three lines. Without `-u` the commits still arrive and the config
is not written — so the branch is published and untracked, which looks identical
in `git log --decorate --all` and different in every command that compares you to
the remote.

```
$ git branch -vv
* feature/csv-upload a382308 Skip the header row                      # untracked
* feature/csv-upload a382308 [origin/feature/csv-upload] Skip the ...  # tracked
```

## What tracking buys

- `git status` says `Your branch is ahead of 'origin/feature/csv-upload' by 2
  commits`. Untracked, it says nothing — and "nothing" reads exactly like "no
  difference".
- bare `git push` and `git pull` work. Untracked, `git pull` says `There is no
  tracking information for the current branch`.
- `@{u}` resolves, which is what this exercise's `upstream-is-recorded` check
  reads. So do `git log @{u}..HEAD` ("what have I not pushed") and
  `git diff @{u}` — both worth knowing, both unavailable without an upstream.

`git branch --set-upstream-to=origin/feature/csv-upload` sets it after the fact
if you forgot, and:

```
git config --global push.autoSetupRemote true
```

makes `git push` set it automatically on the first push of any branch. Since git
2.37 this is the setting that makes `-u` unnecessary, and there is no good
reason not to turn it on.

## Watch which branch you are pushing

`git push -u origin main` from a feature branch succeeds, prints
`Everything up-to-date`, and publishes nothing. It is a reassuring message for
an operation that did not do what you wanted — and the reason the second
counter-example here exists.

`git status --short --branch` before pushing prints the branch you are on. One
line, and it is the same habit that prevents the equivalent mistake with
`reset` and `rebase`.

## Publishing is not merging

```
git push -u origin feature/csv-upload      # "please review this"
git checkout main; git merge feature/...   # "I have decided"
```

Both put the work on `origin`. Only the first leaves the decision to somebody
else, which is what a branch is *for*. `not-merged-into-main` is a required
check here because "get it onto origin" has a shorter wrong answer than it has a
right one.

## A note on names

`feature/csv-upload` contains a slash, which makes it a path under
`.git/refs/heads/`. That is all the slash means — git has no notion of branch
hierarchy, just names that happen to nest on disk. It does mean you cannot have
both a branch called `feature` and a branch called `feature/csv-upload`, because
one would have to be a file and a directory at once.
