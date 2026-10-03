# The pickaxe searches for a change, not for a state

`git grep` searches the files you have. `git blame` tells you who last touched a
line that exists. Neither can answer "when did this stop being here", because
the thing you are looking for is absent from every version you can see.

```
git log -S enforce_rate_limit -- middleware.py
```

`-S<string>` lists commits where the **number of occurrences** of that string
changed. A commit that added the call and a commit that removed it both change
the count, so both are listed — newest first, which is how you tell them apart.

```
a382308 Make the middleware chain a list       <- count went 1 -> 0
2b5faf7 Enforce the rate limit on every request <- count went 0 -> 1
```

A commit that merely moved the line within the file does *not* appear, because
the count did not change. That is usually what you want, and occasionally it is
the reason you cannot find anything.

## `-S` and `-G`

| flag | matches | use when |
|---|---|---|
| `-S<string>` | commits where the count of `<string>` changed | a thing appeared or vanished |
| `-G<regex>` | commits whose diff *mentions* the pattern at all | the line was edited, not added or removed |

`-G` is the broader one: it hits any commit whose diff touches a matching line,
including pure moves and reformatting. Start with `-S`, which is quieter, and
widen to `-G` when `-S` comes back empty.

Both accept `--pickaxe-regex` to treat `-S` as a pattern rather than a literal
string, and both take a path after `--`, which is almost always worth adding.

## The right tool for the right question

This is the companion to
[`git/find-the-first-bad-commit-with-bisect`](../find-the-first-bad-commit-with-bisect/notes.md),
and the pair is the actual lesson:

| what you know | the tool |
|---|---|
| a string that appeared or vanished | `git log -S` |
| a line that exists and is wrong | `git blame` |
| a behaviour you can test, cause unknown | `git bisect` |
| a file that is gone | `git log --diff-filter=D -- <path>` |

Reaching for `bisect` when a pickaxe would do costs a dozen checkouts. Reaching
for `grep` when the thing is absent from every checkout finds nothing at all,
which is worse, because it looks like an answer.

## Read the commit before you believe the search

The commit the pickaxe finds here is titled *"Make the middleware chain a
list"*. It is a genuine refactor, it changes several lines, and the removed
guard is one of them. Nothing in its message mentions rate limiting, which is
precisely why the search was necessary and why `git show` on it is the step
that turns a hash into an explanation:

- was the line removed deliberately, with the behaviour moved elsewhere?
- was it dropped by accident during a mechanical change?
- is this a revert of something that was itself a mistake?

Those are three different tickets, and only the diff says which. A search result
is a lead, not a verdict.

## Why this ends with a tag

The search output is a hash in your scrollback. `git tag culprit <rev>` writes
it into the repository, which is what lets you reference it in a ticket, diff
against it, or hand it to someone else. A branch or a line in the issue works
just as well — the point is that the expensive part was finding it, and the
result should outlive the terminal.
