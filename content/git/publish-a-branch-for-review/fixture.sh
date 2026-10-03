#!/usr/bin/env bash
# A finished feature branch that exists only on this machine. origin has main
# and nothing else.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# intake' \
  '' \
  'Supplier catalogue intake.'

commit_as c1 "Add project skeleton"

write_file catalogue.py \
  '"""The catalogue."""' \
  '' \
  '' \
  'def products():' \
  '    """Every product, as dicts."""' \
  '    return []'

commit_as c2 "Add the catalogue"

mkremote origin
publish origin main

# --- the branch, finished and unpublished --------------------------------
git checkout --quiet -b feature/csv-upload

write_file upload.py \
  '"""CSV upload."""' \
  '' \
  '' \
  'def read_rows(text):' \
  '    """One product per line: sku, name, price."""' \
  '    return [line.split(",") for line in text.splitlines() if line]'

commit_as u1 "Read products from a CSV upload"

write_file upload.py \
  '"""CSV upload."""' \
  '' \
  '' \
  'HEADER = ("sku", "name", "price")' \
  '' \
  '' \
  'def read_rows(text):' \
  '    """One product per line, with the header row skipped."""' \
  '    rows = [line.split(",") for line in text.splitlines() if line]' \
  '    if rows and tuple(rows[0]) == HEADER:' \
  '        return rows[1:]' \
  '    return rows'

commit_as u2 "Skip the header row if there is one"
