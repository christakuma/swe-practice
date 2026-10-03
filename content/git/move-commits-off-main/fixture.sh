#!/usr/bin/env bash
# Two commits of feature work made directly on main by someone who forgot to
# branch first. Unpushed: origin/main is still at the skeleton commit, which is
# why the branch pointer can still be moved.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# ledger' \
  '' \
  'Double-entry bookkeeping, badly.'

write_file ledger.py \
  '"""Accounts and entries."""' \
  '' \
  '' \
  'def balance(entries):' \
  '    """Sum of every entry amount."""' \
  '    return sum(entry["amount"] for entry in entries)'

commit_as c1 "Add project skeleton"

mkremote origin
publish origin main

# --- c2, c3: feature work that was never meant to land on main -------------
write_file export.py \
  '"""CSV export, which is a feature and not a fix."""' \
  '' \
  '' \
  'def to_csv(entries):' \
  '    """One line per entry: name, then amount."""' \
  '    rows = []' \
  '    for entry in entries:' \
  '        rows.append(entry["name"] + "," + str(entry["amount"]))' \
  '    return "\n".join(rows)'

commit_as c2 "Start CSV export"

write_file export.py \
  '"""CSV export, which is a feature and not a fix."""' \
  '' \
  '' \
  'HEADER = "name,amount"' \
  '' \
  '' \
  'def to_csv(entries):' \
  '    """One line per entry, with a header row first."""' \
  '    rows = [HEADER]' \
  '    for entry in entries:' \
  '        rows.append(entry["name"] + "," + str(entry["amount"]))' \
  '    return "\n".join(rows)'

commit_as c3 "Add header row to CSV export"
