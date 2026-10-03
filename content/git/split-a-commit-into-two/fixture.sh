#!/usr/bin/env bash
# One commit doing two unrelated things: a bug fix and a changelog entry. Not
# pushed, so the commit can be taken apart rather than merely apologised for.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# tzconv' \
  '' \
  'Timezone conversion for the scheduler.'

commit_as c1 "Add project skeleton"

write_file convert.py \
  '"""Timezone conversion."""' \
  '' \
  '' \
  'def to_utc(naive, offset_hours):' \
  '    """Shift a naive timestamp to UTC."""' \
  '    return naive + offset_hours * 3600'

commit_as c2 "Add timezone conversion"

mkremote origin
publish origin main

# --- c3: the commit that should have been two ----------------------------
# The sign was wrong -- a +02:00 offset was being added instead of subtracted
# -- and the same commit also starts a changelog.
write_file convert.py \
  '"""Timezone conversion."""' \
  '' \
  '' \
  'def to_utc(naive, offset_hours):' \
  '    """Shift a naive timestamp to UTC."""' \
  '    return naive - offset_hours * 3600'

write_file CHANGELOG.md \
  '# Changelog' \
  '' \
  '## Unreleased' \
  '' \
  '- Timezone conversion now subtracts the offset.'

commit_as c3 "Fix offset sign and start a changelog"
