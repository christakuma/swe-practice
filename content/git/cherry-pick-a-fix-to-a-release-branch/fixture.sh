#!/usr/bin/env bash
# A release branch cut three commits ago, and a main that has since picked up
# two features and one bug fix. Only the fix is allowed onto the release.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# billing' \
  '' \
  'Invoice totals. 1.x is in production.'

write_file billing.py \
  '"""Invoice totals."""' \
  '' \
  '' \
  'def total(lines):' \
  '    """Sum of the line amounts."""' \
  '    amount = sum(line["amount"] for line in lines)' \
  '    return amount'

commit_as c1 "Add invoice totals"

# The release was cut here and has not moved since.
git branch release/1.x

write_file feature_flags.py \
  '"""Feature flags, read once at startup."""' \
  '' \
  '' \
  'FLAGS = {"new_checkout": False, "metered_billing": False}' \
  '' \
  '' \
  'def enabled(name):' \
  '    """Whether a flag is on."""' \
  '    return FLAGS.get(name, False)'

commit_as c2 "Add feature flags"

# --- the fix that has to be backported ------------------------------------
# Half a penny per line adds up: production has been under-billing since 1.0.
write_file billing.py \
  '"""Invoice totals."""' \
  '' \
  '' \
  'def total(lines):' \
  '    """Sum of the line amounts, rounded to the penny."""' \
  '    amount = sum(line["amount"] for line in lines)' \
  '    return round(amount, 2)'

commit_as c3 "Fix rounding of invoice totals"

write_file upload.py \
  '"""Bulk invoice upload."""' \
  '' \
  '' \
  'def parse(rows):' \
  '    """One invoice per row."""' \
  '    return [{"amount": float(row[1]), "name": row[0]} for row in rows]'

commit_as c4 "Add bulk invoice upload"
