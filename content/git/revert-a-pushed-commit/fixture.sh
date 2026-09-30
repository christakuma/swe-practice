#!/usr/bin/env bash
# A three-commit project whose most recent commit is already on origin and
# breaks the build. The teammate who pulled it is implied by the constraint,
# not modelled -- what matters is that c3 must stay reachable.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

# --- c1: project skeleton --------------------------------------------------
write_file README.md \
  '# invoice-tool' \
  '' \
  'Parses invoice CSV lines. Run ./build.sh to check it still works.'

write_file build.sh \
  '#!/usr/bin/env bash' \
  'set -e' \
  '# The build asserts the parser still exposes the function it promises.' \
  'grep -q "def parse_line" parser.py' \
  'echo "build ok"'

commit_as c1 "Add project skeleton and build check"

# --- c2: a working parser --------------------------------------------------
write_file parser.py \
  'def parse_line(line):' \
  '    """Split one CSV line into (name, amount)."""' \
  '    name, amount = line.split(",")' \
  '    return name, int(amount)'

commit_as c2 "Add CSV line parser"

# --- c3: the bad refactor --------------------------------------------------
# Renames the function without updating build.sh. Everything still "looks"
# fine in the diff, which is exactly why it got pushed.
write_file parser.py \
  'def parse(line):' \
  '    """Split one CSV line into (name, amount)."""' \
  '    name, amount = line.split(",")' \
  '    return name, int(amount)'

commit_as c3 "Rename parse_line to parse"

# --- publish, so the damage is shared -------------------------------------
mkremote origin
publish origin main
