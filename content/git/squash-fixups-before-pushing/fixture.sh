#!/usr/bin/env bash
# Three local commits where there should be one: a feature and two fixups for
# typos in it. origin/main is pinned at c1, so the whole mess is unpublished --
# which is the precondition that makes squashing legal at all.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# gateway' \
  '' \
  'Request throttling for the public API.'

commit_as c1 "Add project skeleton"

mkremote origin
publish origin main

write_file limiter.py \
  '"""A token bucket rate limiter."""' \
  '' \
  '' \
  'class Limiter:' \
  '    """Allows a burst up to `capacity`, then refills at a steady rate."""' \
  '' \
  '    def __init__(self, capcity, refill_per_second):' \
  '        self.capacity = capcity' \
  '        self.refill_per_second = refill_per_second' \
  '        self.tokens = capcity' \
  '' \
  '    def allow(self, cost=1):' \
  '        """Whether a request costing `cost` tokens may proceed."""' \
  '        if self.tokens >= cost:' \
  '            self.tokens -= cost' \
  '            return True' \
  '        return False'

commit_as c2 "Add rate limiter"

write_file limiter.py \
  '"""A token bucket rate limiter."""' \
  '' \
  '' \
  'class Limiter:' \
  '    """Allows a burst up to `capacity`, then refills at a steady rate."""' \
  '' \
  '    def __init__(self, capacity, refill_per_second):' \
  '        self.capacity = capacity' \
  '        self.refill_per_second = refill_per_second' \
  '        self.tokens = capacity' \
  '' \
  '    def allow(self, cost=1):' \
  '        """Whether a request costing `cost` tokens may proceed."""' \
  '        if self.tokens >= cost:' \
  '            self.tokens -= cost' \
  '            return True' \
  '        return False'

commit_as c3 "fix typo"

write_file README.md \
  '# gateway' \
  '' \
  'Request throttling for the public API.' \
  '' \
  'See limiter.py for the token bucket.'

commit_as c4 "fix typo again"
