#!/usr/bin/env bash
# A branch deleted with -D while it still had two unmerged commits on it, and
# then some ordinary work on main so the deletion is not the most recent thing
# that happened. Nothing was ever pushed.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# postbox' \
  '' \
  'Outbound webhooks for the events pipeline.'

commit_as c1 "Add project skeleton"

# --- the branch, and the work on it ---------------------------------------
git checkout --quiet -b feature/webhooks

write_file webhook.py \
  '"""Outbound webhook delivery."""' \
  '' \
  '' \
  'def deliver(url, payload):' \
  '    """POST the payload. Returns the status code."""' \
  '    return 200'

commit_as w1 "Add webhook delivery"

write_file webhook.py \
  '"""Outbound webhook delivery."""' \
  '' \
  '' \
  'MAX_ATTEMPTS = 5' \
  '' \
  '' \
  'def deliver(url, payload):' \
  '    """POST the payload. Returns the status code."""' \
  '    return 200' \
  '' \
  '' \
  'def deliver_with_retry(url, payload):' \
  '    """Retry on anything that is not a 2xx, up to MAX_ATTEMPTS times."""' \
  '    for attempt in range(MAX_ATTEMPTS):' \
  '        status = deliver(url, payload)' \
  '        if 200 <= status < 300:' \
  '            return status' \
  '    return status'

commit_as w2 "Retry failed webhook deliveries"

# --- back to main, and then the mistake -----------------------------------
git checkout --quiet main

write_file README.md \
  '# postbox' \
  '' \
  'Outbound webhooks for the events pipeline.' \
  '' \
  'Deployed from main. See CONTRIBUTING for the branch naming convention.'

commit_as c2 "Document where deploys come from"

# Tidying up branches after a release. This one was not merged.
git branch -D feature/webhooks --quiet
