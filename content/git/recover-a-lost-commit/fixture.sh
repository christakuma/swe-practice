#!/usr/bin/env bash
# Two commits of unpushed work destroyed by a reset --hard, then enough
# subsequent activity that HEAD@{1} is NOT the answer. Recovering this
# requires actually reading the reflog, not guessing at the last entry.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

# --- c1: skeleton on main --------------------------------------------------
write_file README.md \
  '# invoice-tool' \
  '' \
  'Parses and exports invoice data.'

commit_as c1 "Add project skeleton"

# --- c2, c3: an afternoon of work on a feature branch ---------------------
git switch --quiet -c feature/csv-export

write_file exporter.py \
  'import csv' \
  '' \
  '' \
  'def export_rows(rows, path):' \
  '    """Write rows to a CSV file, header first."""' \
  '    with open(path, "w", newline="") as handle:' \
  '        writer = csv.writer(handle)' \
  '        writer.writerow(["name", "amount"])' \
  '        writer.writerows(rows)'

commit_as c2 "Add CSV exporter"

write_file test_exporter.py \
  'from exporter import export_rows' \
  '' \
  '' \
  'def test_writes_header_and_rows(tmp_path):' \
  '    out = tmp_path / "invoices.csv"' \
  '    export_rows([("acme", 120)], out)' \
  '    assert out.read_text().splitlines()[0] == "name,amount"'

commit_as c3 "Add tests for CSV exporter"

# --- the disaster ----------------------------------------------------------
# Meant to rebase the branch onto main. Typed reset. Nothing was ever pushed,
# so there is no remote copy to fall back on.
git reset --hard --quiet main

# --- and then some ordinary activity on top -------------------------------
# This is the part that makes the exercise real: by the time you notice, the
# reset is no longer the most recent reflog entry.
git switch --quiet main
git switch --quiet feature/csv-export
