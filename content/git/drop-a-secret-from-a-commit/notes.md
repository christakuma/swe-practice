# Untracking is not deleting, and a new commit is not a fix

Two distinctions, and this exercise is only hard if you have not separated them.

## `git rm` versus `git rm --cached`

```
git rm .env           # stages a deletion AND deletes the file
git rm --cached .env  # stages a deletion, leaves the file alone
```

`--cached` means "act on the index only". The file becomes untracked and stays
exactly where it is, which is what you want for anything that is *supposed* to
exist locally and never be committed: `.env`, a local database, an editor
directory.

The shorter command is the destructive one. That is worth knowing because
`deploy.sh` reads `.env` — so `git rm .env` leaves you with a clean-looking
repository and a deploy that fails on the next run, in a way that has nothing
obvious to do with the git command you typed ten minutes earlier.

## Removing a file versus removing it from history

```
            a new commit                     an amend

d2261fe c1  <- origin/main       d2261fe c1  <- origin/main
2b5faf7 c2  "Add deploy script"  a382308 c2* "Add deploy script"  <- main
            (contains .env)                  (no .env)
42dc386 c3  "Stop tracking .env" (2b5faf7 unreachable from any branch)
            <- main
```

The left-hand history has no `.env` in its tip and the token is still in it.
`git show HEAD~1` prints it. So does `git log -p`. So does a fresh clone, which
copies every reachable commit, and so does any CI job that checks out the
branch. Deleting a file in git never removes the old content — it adds a commit
saying the file is gone.

The right-hand history does not contain the token at all, because the commit
that held it is no longer reachable from any branch. That is what
`secret-not-in-history` checks, and it is why the exercise is phrased as
"nothing has been pushed".

## What to do when it *has* been pushed

Then this exercise's answer does not apply, and the honest order of operations
is:

1. **Rotate the credential.** Immediately, before anything else. Assume it is
   compromised — it is in a clone, a CI cache, a fork, a backup, a notification
   email with the diff in it. Every later step is tidying up; this one is the
   actual remediation.
2. Remove it from history with `git filter-repo` (or BFG), which rewrites every
   affected commit, and coordinate the force-push with everyone who has a clone.
3. Add the `.gitignore` entry so it cannot recur.

Steps 2 and 3 do not make the old token safe. Only step 1 does. People reliably
do them in the opposite order, spend a day rewriting history, and leave a live
token in a fork they did not know about.

## Why `.gitignore` is a required check

Untracking a file is a one-time act; ignoring it is the thing that holds. Without
the ignore rule, `.env` sits untracked in the working directory, and the next
`git add -A` — by you, or by anyone following a README that says to run it —
stages it again. The two steps look redundant and are not: one fixes the past,
one fixes the future.

The amend is also why `.gitignore` had to be staged *before* committing.
`git commit --amend` builds a commit from the index, so a `.gitignore` you wrote
and did not `git add` is simply not in it — and the amend succeeds anyway, which
is the quiet failure mode this exercise shares with
[`git/amend-the-last-commit`](../amend-the-last-commit/notes.md).
