#!/usr/bin/env bash
# Your own feature branch, pushed, then squashed locally -- and a colleague has
# pushed a review fix to the same branch in the meantime.
#
# The remote-tracking ref is wound back after the colleague's push, so this
# clone believes origin/feature/search-ui is still at s2. That gap is what
# --force-with-lease exists to notice.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# shelf' \
  '' \
  'Catalogue browsing for the storefront.'

commit_as c1 "Add project skeleton"

write_file app.py \
  '"""The storefront."""' \
  '' \
  '' \
  'def render(page):' \
  '    """Render one page."""' \
  '    return page'

commit_as c2 "Add the storefront"

mkremote origin
publish origin main

# --- your branch, two commits, pushed ------------------------------------
git checkout --quiet -b feature/search-ui

write_file search_ui.py \
  '"""The search box."""' \
  '' \
  '' \
  'def search_box(placeholder="Search the catalogue"):' \
  '    """The markup for the search input."""' \
  '    return {"tag": "input", "placeholder": placeholder}'

commit_as s1 "Add the search box"

write_file search_ui.py \
  '"""The search box."""' \
  '' \
  '' \
  'SHORTCUT = "slash"' \
  '' \
  '' \
  'def search_box(placeholder="Search the catalogue"):' \
  '    """The markup for the search input."""' \
  '    return {"tag": "input", "placeholder": placeholder, "hotkey": SHORTCUT}'

commit_as s2 "Focus the search box on the slash key"

publish origin feature/search-ui

# --- the colleague review fix, pushed to YOUR branch ---------------------
# A new file, so nothing it does can conflict with the squash below.
git checkout --quiet -b colleague

write_file test_search_ui.py \
  'from search_ui import search_box' \
  '' \
  '' \
  'def test_the_search_box_announces_its_hotkey():' \
  '    assert search_box()["hotkey"] == "slash"'

commit_as r1 "Add a test for the search box hotkey"

git push --quiet origin colleague:feature/search-ui

# Wind the remote-tracking ref back to before their push, so this clone is as
# out of date as it would really be.
git update-ref refs/remotes/origin/feature/search-ui \
  "$(git rev-parse feature/search-ui)"

git checkout --quiet feature/search-ui
git branch --quiet -D colleague

# --- your tidy-up, done in ignorance of the review fix -------------------
# Two commits squashed into one. Perfectly reasonable on a branch you believe
# is yours alone.
git reset --quiet --soft HEAD~2
commit_as s12 "Add the search box, focused on the slash key"
