#!/usr/bin/env bash
# A feature branch merged into main with --no-ff and pushed. The discount rules
# turn out to be wrong and have to come off main today; the branch itself is
# fine and will be fixed and merged again later.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# tillroll' \
  '' \
  'Point of sale pricing.'

commit_as c1 "Add project skeleton"

write_file pricing.py \
  '"""Line pricing."""' \
  '' \
  '' \
  'def line_total(unit_price, quantity):' \
  '    """Price for one order line."""' \
  '    return unit_price * quantity'

commit_as c2 "Add line pricing"

# --- the feature branch ---------------------------------------------------
git checkout --quiet -b feature/discounts

write_file discounts.py \
  '"""Volume discounts."""' \
  '' \
  '' \
  'TIERS = ((100, 0.10), (50, 0.05))' \
  '' \
  '' \
  'def discount_for(quantity):' \
  '    """The discount rate for this quantity."""' \
  '    for threshold, rate in TIERS:' \
  '        if quantity >= threshold:' \
  '            return rate' \
  '    return 0.0'

commit_as d1 "Add volume discount tiers"

write_file pricing.py \
  '"""Line pricing."""' \
  '' \
  '' \
  'from discounts import discount_for' \
  '' \
  '' \
  'def line_total(unit_price, quantity):' \
  '    """Price for one order line, after any volume discount."""' \
  '    gross = unit_price * quantity' \
  '    return gross * (1 - discount_for(quantity))'

commit_as d2 "Apply discounts to line totals"

# --- merged into main, and published -------------------------------------
git checkout --quiet main
git merge --quiet --no-ff --no-edit feature/discounts

mkremote origin
publish origin main
