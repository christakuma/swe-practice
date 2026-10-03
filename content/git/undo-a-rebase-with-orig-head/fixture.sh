#!/usr/bin/env bash
# A feature branch that was pushed and then rebased, which rewrote commits a
# colleague already has. The fixture performs the rebase, so the repository the
# solver opens is already in the state that needs undoing -- and ORIG_HEAD is
# sitting there holding the answer.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# gatehouse' \
  '' \
  'Authentication for the admin console.'

commit_as c1 "Add project skeleton"

write_file session.py \
  '"""Session cookies."""' \
  '' \
  '' \
  'def issue(user_id):' \
  '    """A signed session token for this user."""' \
  '    return f"session-{user_id}"'

commit_as c2 "Add session issuing"

# --- the feature branch, pushed and shared --------------------------------
git checkout --quiet -b feature/mfa

write_file mfa.py \
  '"""Second factor, time based."""' \
  '' \
  '' \
  'def code(secret, step):' \
  '    """Six digits from the secret and the time step."""' \
  '    return str((hash(secret) + step) % 1000000).zfill(6)'

commit_as f1 "Add time-based code generation"

write_file mfa.py \
  '"""Second factor, time based."""' \
  '' \
  '' \
  'WINDOW = 1' \
  '' \
  '' \
  'def code(secret, step):' \
  '    """Six digits from the secret and the time step."""' \
  '    return str((hash(secret) + step) % 1000000).zfill(6)' \
  '' \
  '' \
  'def verify(secret, step, given):' \
  '    """Accept a code from the previous or next step too."""' \
  '    nearby = range(step - WINDOW, step + WINDOW + 1)' \
  '    return any(code(secret, s) == given for s in nearby)'

commit_as f2 "Accept codes from the adjacent window"

mkremote origin
publish origin feature/mfa

git checkout --quiet main
write_file session.py \
  '"""Session cookies."""' \
  '' \
  '' \
  'TTL_SECONDS = 3600' \
  '' \
  '' \
  'def issue(user_id):' \
  '    """A signed session token for this user."""' \
  '    return f"session-{user_id}"'

commit_as m1 "Give sessions a TTL"

publish origin main

# --- the rebase that should not have happened -----------------------------
# Rewrites f1 and f2, which origin/feature/mfa still holds, and which a
# colleague pulled this morning.
git checkout --quiet feature/mfa
git rebase --quiet main
