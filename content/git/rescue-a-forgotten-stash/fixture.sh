#!/usr/bin/env bash
# A stash made on Tuesday and forgotten, with two commits of unrelated work on
# top of it. The stash holds the only copy of the timeout handling.
#
# Note the fixture ends with a clean worktree: `git stash push` is what makes
# that true, and it is also what makes the work invisible to `git log`.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# fetcher' \
  '' \
  'Pulls supplier catalogues over HTTP.'

write_file client.py \
  '"""HTTP client for supplier catalogues."""' \
  '' \
  '' \
  'def fetch(url):' \
  '    """Return the body at url."""' \
  '    return request(url)' \
  '' \
  '' \
  'def request(url):' \
  '    """Stand-in for the real transport."""' \
  '    return ""'

commit_as c1 "Add the catalogue client"

# --- the work that got stashed --------------------------------------------
# Half finished: the timeout is threaded through but nothing retries yet.
write_file client.py \
  '"""HTTP client for supplier catalogues."""' \
  '' \
  '' \
  'DEFAULT_TIMEOUT = 10' \
  '' \
  '' \
  'def fetch(url, timeout=DEFAULT_TIMEOUT):' \
  '    """Return the body at url, giving up after timeout seconds."""' \
  '    return request(url, timeout)' \
  '' \
  '' \
  'def request(url, timeout):' \
  '    """Stand-in for the real transport."""' \
  '    return ""'

git stash push --quiet -m "wip: timeout handling"

# --- and then two days of other work --------------------------------------
write_file catalogue.py \
  '"""Parsing a supplier catalogue."""' \
  '' \
  '' \
  'def parse(body):' \
  '    """One product per line."""' \
  '    return [line for line in body.splitlines() if line]'

commit_as c2 "Add catalogue parsing"

write_file README.md \
  '# fetcher' \
  '' \
  'Pulls supplier catalogues over HTTP and parses them.'

commit_as c3 "Mention parsing in the README"
