#!/usr/bin/env bash
# Two branches that changed the same region of one config file. main raised the
# worker count and added a timeout; the branch raised the worker count further,
# having actually measured it. Merging them conflicts, and neither side alone
# is the right answer.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# relay' \
  '' \
  'Message relay. Tuning lives in settings.ini.'

write_file settings.ini \
  '[server]' \
  'host = 0.0.0.0' \
  'port = 8080' \
  'workers = 2'

commit_as c1 "Add the relay and its settings"

# --- the colleague branch: a measured worker count ------------------------
git checkout --quiet -b feature/tune

write_file settings.ini \
  '[server]' \
  'host = 0.0.0.0' \
  'port = 8080' \
  'workers = 8'

commit_as f1 "Raise workers to 8 after load testing"

# --- main: a guess, plus a timeout nobody else added ----------------------
git checkout --quiet main

write_file settings.ini \
  '[server]' \
  'host = 0.0.0.0' \
  'port = 8080' \
  'workers = 4' \
  'timeout_seconds = 30'

commit_as m1 "Raise workers to 4 and add a request timeout"
