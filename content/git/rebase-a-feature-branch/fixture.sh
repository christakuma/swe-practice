#!/usr/bin/env bash
# A feature branch two commits long, branched from a main that has since moved
# on. The two sides touch different files, so the rebase this exercise asks for
# is the uncomplicated kind -- the lesson is what rebase does to the shape of
# history, not how to resolve a conflict.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# analytics' \
  '' \
  'Reports over the events table.'

commit_as c1 "Add project skeleton"

write_file events.py \
  '"""The events table, such as it is."""' \
  '' \
  '' \
  'def load(path):' \
  '    """One event per line, tab separated."""' \
  '    with open(path, encoding="utf-8") as handle:' \
  '        return [line.rstrip().split("\t") for line in handle]'

commit_as c2 "Add event loading"

# --- the feature branch, cut from c2 --------------------------------------
git checkout --quiet -b feature/report

write_file report.py \
  '"""Monthly reporting."""' \
  '' \
  '' \
  'def monthly(events):' \
  '    """Count events per calendar month."""' \
  '    counts = {}' \
  '    for event in events:' \
  '        month = event[0][:7]' \
  '        counts[month] = counts.get(month, 0) + 1' \
  '    return counts'

commit_as f1 "Add monthly report"

write_file report.py \
  '"""Monthly reporting."""' \
  '' \
  '' \
  'def monthly(events):' \
  '    """Count events per calendar month, newest month first."""' \
  '    counts = {}' \
  '    for event in events:' \
  '        month = event[0][:7]' \
  '        counts[month] = counts.get(month, 0) + 1' \
  '    return dict(sorted(counts.items(), reverse=True))'

commit_as f2 "Sort the monthly report"

# --- main moves on while the branch is open -------------------------------
git checkout --quiet main

write_file events.py \
  '"""The events table, such as it is."""' \
  '' \
  '' \
  'def load(path):' \
  '    """One event per line, tab separated. Blank lines are skipped."""' \
  '    with open(path, encoding="utf-8") as handle:' \
  '        rows = [line.rstrip() for line in handle]' \
  '    return [row.split("\t") for row in rows if row]'

commit_as m1 "Skip blank lines when loading events"

mkremote origin
publish origin main
