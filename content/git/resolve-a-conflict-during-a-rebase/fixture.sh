#!/usr/bin/env bash
# A two-commit feature branch whose first commit touches the same constants
# main has since changed. Rebasing stops on that commit; the second one applies
# cleanly, so the rebase stops exactly once.
#
# retry.py is five lines when resolved, and that is on purpose. The console's
# only editor is `write`, which replaces a file, so the resolution is typed
# whole -- and at fifteen lines, which is what this was, the exercise graded
# typing. Small enough that both sides land in one conflict block, which is
# also the more honest picture: everything to be decided is between the markers.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# courier' \
  '' \
  'Delivery callbacks, with retries.'

write_file retry.py \
  'MAX_ATTEMPTS = 3'

commit_as c1 "Add the retry policy"

# --- the feature branch ---------------------------------------------------
git checkout --quiet -b feature/backoff

write_file retry.py \
  'MAX_ATTEMPTS = 5' \
  '' \
  'def backoff_seconds(attempt):' \
  '    return 2 ** attempt'

commit_as f1 "Back off exponentially, and allow five attempts"

write_file jitter.py \
  '"""Randomised delay, so retries from many workers do not align."""' \
  '' \
  '' \
  'def jitter(seconds):' \
  '    """Up to a quarter of the delay, added on."""' \
  '    return seconds * 1.25'

commit_as f2 "Add jitter to the backoff"

# --- main, which changed the same constants block ------------------------
git checkout --quiet main

write_file retry.py \
  'MAX_ATTEMPTS = 4' \
  'RETRY_ON = (500, 502, 503, 504)'

commit_as m1 "Only retry on gateway errors"
