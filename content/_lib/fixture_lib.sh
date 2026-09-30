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

set -euo pipefail

: "${PRACTICE_ALIASES:?fixture must be run by the provisioner}"
: "${PRACTICE_REMOTES:?fixture must be run by the provisioner}"

_practice_clock=0
_practice_epoch=1709542800    # 2024-03-04T09:00:00Z

# Deterministic, monotonic commit timestamps.
#
# Git accepts "@<epoch> <tz>" for dates, which sidesteps every portability
# problem with date arithmetic in shell. Same fixture in, same SHAs out -- on
# every run and every platform -- while git log still shows a plausible
# history instead of ten commits at the same instant.
_practice_tick() {
  _practice_clock=$(( _practice_clock + 1 ))
  local ts=$(( _practice_epoch + _practice_clock * 420 ))
  export GIT_AUTHOR_DATE="@${ts} +0000"
  export GIT_COMMITTER_DATE="@${ts} +0000"
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
