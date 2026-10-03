#!/usr/bin/env bash
# A two-commit feature branch whose first commit touches the same constants
# main has since changed. Rebasing stops on that commit; the second one applies
# cleanly, so the rebase stops exactly once.
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
  '"""Retry policy for delivery callbacks."""' \
  '' \
  '' \
  'MAX_ATTEMPTS = 3' \
  '' \
  '' \
  'def should_retry(status, attempt):' \
  '    """Whether to try again after this response."""' \
  '    return attempt in range(MAX_ATTEMPTS)'

commit_as c1 "Add the retry policy"

# --- the feature branch ---------------------------------------------------
git checkout --quiet -b feature/backoff

write_file retry.py \
  '"""Retry policy for delivery callbacks."""' \
  '' \
  '' \
  'MAX_ATTEMPTS = 5' \
  '' \
  '' \
  'def backoff_seconds(attempt):' \
  '    """Wait longer after each failure."""' \
  '    return 2 ** attempt' \
  '' \
  '' \
  'def should_retry(status, attempt):' \
  '    """Whether to try again after this response."""' \
  '    return attempt in range(MAX_ATTEMPTS)'

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
  '"""Retry policy for delivery callbacks."""' \
  '' \
  '' \
  'MAX_ATTEMPTS = 4' \
  'RETRY_ON = (500, 502, 503, 504)' \
  '' \
  '' \
  'def should_retry(status, attempt):' \
  '    """Whether to try again after this response."""' \
  '    return status in RETRY_ON and attempt in range(MAX_ATTEMPTS)'

commit_as m1 "Only retry on gateway errors"
