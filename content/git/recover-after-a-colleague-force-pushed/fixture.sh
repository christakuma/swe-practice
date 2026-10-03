#!/usr/bin/env bash
# A shared branch whose two commits a colleague has squashed into one and
# force-pushed, while this clone has a commit of its own on top of the
# originals. You have fetched, so the divergence is visible.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# dispatch' \
  '' \
  'Outbound notifications.'

commit_as c1 "Add project skeleton"

write_file dispatch.py \
  '"""Notification dispatch."""' \
  '' \
  '' \
  'def send(message):' \
  '    """Deliver one message."""' \
  '    return True'

commit_as c2 "Add dispatch"

mkremote origin
publish origin main

# --- the shared branch, as the colleague first pushed it -----------------
git checkout --quiet -b feature/webhooks

write_file webhook.py \
  '"""Webhook delivery."""' \
  '' \
  '' \
  'def deliver(url, payload):' \
  '    """POST the payload."""' \
  '    return 200'

commit_as k1 "Add webhook delivery"

write_file webhook.py \
  '"""Webhook delivery."""' \
  '' \
  '' \
  'TIMEOUT = 5' \
  '' \
  '' \
  'def deliver(url, payload):' \
  '    """POST the payload, giving up after TIMEOUT seconds."""' \
  '    return 200'

commit_as k2 "Give webhook delivery a timeout"

publish origin feature/webhooks

# --- your commit, on top of the originals --------------------------------
write_file signing.py \
  '"""Payload signing, so receivers can verify us."""' \
  '' \
  '' \
  'def sign(payload, secret):' \
  '    """A hex digest over the payload."""' \
  '    return hex(hash((payload, secret)))'

commit_as y1 "Sign webhook payloads"

# --- the colleague squashes the branch and force-pushes ------------------
# Built from main -- which is still at c2 -- so that k1 and k2 are genuinely
# replaced rather than extended. `main`, not `c2`: an alias is ours and lives
# in the alias file, so git has never heard of it.
git checkout --quiet -b colleague main

write_file webhook.py \
  '"""Webhook delivery."""' \
  '' \
  '' \
  'TIMEOUT = 5' \
  '' \
  '' \
  'def deliver(url, payload):' \
  '    """POST the payload, giving up after TIMEOUT seconds."""' \
  '    return 200'

commit_as kr1 "Add webhook delivery, with a timeout"

# --force, which is how this situation arises. The push updates this clone's
# remote-tracking ref as a side effect -- which here is realistic: you fetched
# this morning and saw the divergence, which is why you are reading this.
git push --quiet --force origin colleague:feature/webhooks

git checkout --quiet feature/webhooks
git branch --quiet -D colleague
