#!/usr/bin/env bash
# A half-finished feature branch merged into main an hour early. The merge is
# not pushed -- origin/main is still at c2 -- so main can be moved back rather
# than apologised to.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# archivist' \
  '' \
  'Full text search over the document store.'

commit_as c1 "Add project skeleton"

write_file store.py \
  '"""The document store."""' \
  '' \
  '' \
  'def documents():' \
  '    """Every document, as dicts."""' \
  '    return []'

commit_as c2 "Add the document store"

mkremote origin
publish origin main

# --- the branch that is not ready -----------------------------------------
git checkout --quiet -b feature/search

write_file search.py \
  '"""Full text search. NOT FINISHED."""' \
  '' \
  '' \
  'def search(query):' \
  '    """Documents matching query."""' \
  '    raise NotImplementedError("tokenizer still returns substrings")'

commit_as s1 "Start full text search"

# --- merged into main by mistake -----------------------------------------
git checkout --quiet main
git merge --quiet --no-ff --no-edit feature/search
