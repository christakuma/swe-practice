#!/usr/bin/env bash
# Helpers available to every fixture, sourced via $PRACTICE_FIXTURE_LIB.
#
# Fixtures are TRUSTED code: you author them, so they get a real shell.
# User commands are not -- see docs/PLAN.md section 8.1 for the trust split.
#
# Provisioner contract (env vars this library requires):
#   PRACTICE_ALIASES   file to append "<alias>=<sha>" lines to
#   PRACTICE_SNAPSHOT  file the provisioner writes refs into after the fixture
#   PRACTICE_REMOTES   directory to create bare "remotes" in
#   PRACTICE_CLOCK     file holding the epoch of the most recent commit
#   PRACTICE_EPOCH     epoch the clock starts from
#   PRACTICE_STEP      seconds between commits

set -euo pipefail

: "${PRACTICE_ALIASES:?fixture must be run by the provisioner}"
: "${PRACTICE_REMOTES:?fixture must be run by the provisioner}"
: "${PRACTICE_CLOCK:?fixture must be run by the provisioner}"

# The clock's parameters come from the provisioner rather than being written
# here, so there is exactly one definition of them (adapters/sandbox/env.py).
# Two copies would drift, and the symptom would be every commit hash in
# content/fixtures.lock changing for no visible reason.
_practice_epoch="${PRACTICE_EPOCH:?fixture must be run by the provisioner}"
_practice_step="${PRACTICE_STEP:?fixture must be run by the provisioner}"
_practice_clock="$_practice_epoch"

# Deterministic, monotonic commit timestamps.
#
# Git accepts "@<epoch> <tz>" for dates, which sidesteps every portability
# problem with date arithmetic in shell. Same fixture in, same SHAs out -- on
# every run and every platform -- while git log still shows a plausible
# history instead of ten commits at the same instant.
#
# The position is written to $PRACTICE_CLOCK after every tick, because the
# clock has to span the whole attempt and not just the fixture: if it stopped
# here, the first commit the SOLVER makes would fall back to wall-clock time
# and the attempt would stop being reproducible (docs/PLAN.md section 6.1).
# This process exits; the file is the only way to tell the sandbox where the
# history got to.
_practice_tick() {
  _practice_clock=$(( _practice_clock + _practice_step ))
  export GIT_AUTHOR_DATE="@${_practice_clock} +0000"
  export GIT_COMMITTER_DATE="@${_practice_clock} +0000"
  printf '%s\n' "$_practice_clock" > "$PRACTICE_CLOCK"
}

# write_file <path> [line ...]
# Always writes LF, regardless of the host platform. Lines are literal.
write_file() {
  local path="$1"; shift
  local dir
  dir="$(dirname "$path")"
  [ "$dir" = "." ] || mkdir -p "$dir"
  if [ "$#" -eq 0 ]; then
    : > "$path"
  else
    printf '%s\n' "$@" > "$path"
  fi
}

# commit_as <alias> <message>
# Stages everything and commits, then records the resulting SHA under a
# symbolic alias so assertions can say "@c2" instead of a literal hash.
commit_as() {
  local alias="$1" message="$2"
  _practice_tick
  git add -A
  git commit --quiet --no-gpg-sign -m "$message"
  printf '%s=%s\n' "$alias" "$(git rev-parse HEAD)" >> "$PRACTICE_ALIASES"
}

# tag_as <tag> [rev]
tag_as() {
  git tag "$1" "${2:-HEAD}"
}

# mkremote <name>
# A "remote" is a local bare repository inside the workspace. There is no
# network in the sandbox, ever.
mkremote() {
  local name="$1"
  git init --quiet --bare "$PRACTICE_REMOTES/$name.git"
  git remote add "$name" "$PRACTICE_REMOTES/$name.git"
}

# publish <remote> <branch>
# Pushes and sets upstream, so the user's plain `git push` works the way it
# would in a real clone.
publish() {
  git push --quiet --set-upstream "$1" "$2"
}
