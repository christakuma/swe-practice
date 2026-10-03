#!/usr/bin/env bash
# Two commits made while HEAD was detached, and then a checkout back to main
# that orphaned them. Git warns loudly when this happens; the warning scrolled
# past half an hour ago.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# atlas' \
  '' \
  'Geocoding lookups, cached.'

commit_as c1 "Add project skeleton"

write_file lookup.py \
  '"""Geocoding lookups."""' \
  '' \
  '' \
  'def geocode(address):' \
  '    """Latitude and longitude for an address."""' \
  '    return (0.0, 0.0)'

commit_as c2 "Add geocoding lookups"

# --- detached, to check something out, and then two commits by mistake ----
git checkout --quiet --detach main

write_file cache.py \
  '"""An in-process cache for geocoding results."""' \
  '' \
  '' \
  'class Cache:' \
  '    """Bounded, least-recently-used."""' \
  '' \
  '    def __init__(self, capacity):' \
  '        self.capacity = capacity' \
  '        self.entries = {}' \
  '' \
  '    def get(self, key):' \
  '        """The cached value, or None."""' \
  '        return self.entries.get(key)'

commit_as d1 "Add a bounded cache"

write_file cache.py \
  '"""An in-process cache for geocoding results."""' \
  '' \
  '' \
  'class Cache:' \
  '    """Bounded, least-recently-used."""' \
  '' \
  '    def __init__(self, capacity):' \
  '        self.capacity = capacity' \
  '        self.entries = {}' \
  '        self.order = []' \
  '' \
  '    def get(self, key):' \
  '        """The cached value, or None. Refreshes recency."""' \
  '        if key in self.entries:' \
  '            self.order.remove(key)' \
  '            self.order.append(key)' \
  '        return self.entries.get(key)' \
  '' \
  '    def put(self, key, value):' \
  '        """Store a value, evicting the least recently used if full."""' \
  '        if len(self.entries) >= self.capacity:' \
  '            oldest = self.order.pop(0)' \
  '            del self.entries[oldest]' \
  '        self.entries[key] = value' \
  '        self.order.append(key)'

commit_as d2 "Evict the least recently used entry"

# --- back to main, which is where the commits became unreachable ---------
git checkout --quiet main
