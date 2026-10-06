#!/usr/bin/env bash
# A tip commit that is not finished and not pushed: a scratch file swept in
# with the real change, and a placeholder subject. origin/main is one commit
# behind on purpose -- amending is only safe because c3 never left this machine,
# and the check that says so needs a published ref to compare against.
#
# The leftover is a whole file rather than a line inside metrics.py, which is
# what it was first. The console's only editor is `write`, which replaces a
# file, so taking one line out meant retyping fifteen -- and a slip there failed
# an attempt on typing rather than on git. `git rm` is one command, and it
# keeps the trap the exercise is about: amend reads the index.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

# --- c1: skeleton ----------------------------------------------------------
write_file README.md \
  '# metrics' \
  '' \
  'Summary statistics for a list of numbers.'

commit_as c1 "Add project skeleton"

# --- c2: the published state ----------------------------------------------
write_file metrics.py \
  '"""Summary statistics for a list of numbers."""' \
  '' \
  '' \
  'def average(values):' \
  '    """The arithmetic mean."""' \
  '    return sum(values) / len(values)'

commit_as c2 "Add average"

mkremote origin
publish origin main

# --- c3: the unfinished tip ------------------------------------------------
# Pushed nowhere. scratch.py and the subject are both leftovers from the half
# hour before the function worked, and `git add .` took the first one along.
write_file metrics.py \
  '"""Summary statistics for a list of numbers."""' \
  '' \
  '' \
  'def average(values):' \
  '    """The arithmetic mean."""' \
  '    return sum(values) / len(values)' \
  '' \
  '' \
  'def median(values):' \
  '    """The middle value, averaging the two middle ones when even."""' \
  '    ordered = sorted(values)' \
  '    middle = len(ordered) // 2' \
  '    if len(ordered) % 2 == 1:' \
  '        return ordered[middle]' \
  '    return (ordered[middle - 1] + ordered[middle]) / 2'

write_file scratch.py \
  'from metrics import median' \
  '' \
  'print("odd ", median([3, 1, 2]))' \
  'print("even", median([4, 1, 3, 2]))'

commit_as c3 "WIP median"
