#!/usr/bin/env bash
# A colleague pushed while you were working. Their commit is on the remote and
# yours is local, so the two have diverged.
#
# Deliberately NOT fetched: refs/remotes/origin/main is left pointing at c2,
# which is what makes the first push rejection a surprise rather than something
# the solver could already see.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# intake' \
  '' \
  'Bulk import of supplier price lists.'

commit_as c1 "Add project skeleton"

write_file importer.py \
  '"""Bulk import."""' \
  '' \
  '' \
  'def import_rows(rows):' \
  '    """Insert every row. Returns how many were inserted."""' \
  '    return len(rows)'

commit_as c2 "Add the importer"

mkremote origin
publish origin main

# --- the colleague commit, pushed straight to the remote ------------------
# Made on a throwaway branch so that the local main never sees it: what lands
# on the remote is r1, and this clone is told nothing about it.
git checkout --quiet -b colleague

write_file validate.py \
  '"""Row validation, applied before import."""' \
  '' \
  '' \
  'REQUIRED = ("sku", "price")' \
  '' \
  '' \
  'def validate(row):' \
  '    """Every required column present and the price a number."""' \
  '    missing = [name for name in REQUIRED if name not in row]' \
  '    if missing:' \
  '        raise ValueError(f"missing columns: {missing}")' \
  '    float(row["price"])'

commit_as r1 "Validate rows before importing them"

git push --quiet origin colleague:main

# Pushing updated this clone's remote-tracking ref as a side effect, so wind it
# back to where a clone that has not fetched since yesterday would have it. The
# remote holds r1; refs/remotes/origin/main says c2. That gap is the normal
# state of any clone whose owner has been working for an hour, and it is what
# makes the first push rejection a surprise.
git update-ref refs/remotes/origin/main "$(git rev-parse main)"

git checkout --quiet main
git branch --quiet -D colleague

# --- and your own commit, which makes it a divergence --------------------
write_file importer.py \
  '"""Bulk import."""' \
  '' \
  '' \
  'BATCH_SIZE = 500' \
  '' \
  '' \
  'def import_rows(rows):' \
  '    """Insert every row in batches. Returns how many were inserted."""' \
  '    inserted = 0' \
  '    for start in range(0, len(rows), BATCH_SIZE):' \
  '        inserted += len(rows[start : start + BATCH_SIZE])' \
  '    return inserted'

commit_as m1 "Insert rows in batches"
