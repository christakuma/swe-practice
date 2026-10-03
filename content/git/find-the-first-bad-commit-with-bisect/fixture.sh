#!/usr/bin/env bash
# Nine commits of capacity tuning, where the worker count and the connection
# pool size are adjusted independently. From c6 onward the two values are
# individually plausible and jointly wrong.
#
# Deliberately NOT greppable: no commit introduces a bad value, so `git log -S`
# has nothing to search for. Deciding whether a commit is good means reading
# both numbers and applying the rule in the README, which is what makes this a
# bisect rather than a search.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# conveyor' \
  '' \
  'Background job runner.' \
  '' \
  '## Capacity rule' \
  '' \
  'Each worker holds two pooled database connections for the whole time it is' \
  'running a job. So the pool has to be big enough for all of them:' \
  '' \
  '    workers * 2 must not exceed pool_size' \
  '' \
  'Break it and the worker that cannot get a connection fails its job with a' \
  'pool timeout instead of retrying, which is what started happening sometime' \
  'this week.'

# capacity <workers> <pool_size> <extra line>
capacity() {
  write_file limits.yaml \
    '# Capacity. See the capacity rule in README.md before changing these.' \
    "workers: $1" \
    "pool_size: $2" \
    'queue_poll_seconds: 5' \
    "$3"
}

capacity 2 8 'log_level: info'
commit_as c1 "Add capacity limits"

capacity 3 8 'log_level: info'
write_file worker.py \
  '"""The job runner."""' \
  '' \
  '' \
  'def run(job):' \
  '    """Run one job to completion."""' \
  '    return job()'
commit_as c2 "Add a third worker and the runner itself"

capacity 3 12 'log_level: info'
commit_as c3 "Grow the connection pool"

capacity 4 12 'log_level: info'
commit_as c4 "Add a fourth worker"

capacity 5 12 'log_level: debug'
commit_as c5 "Add a fifth worker and turn on debug logging"

# --- the first commit where the rule is broken: 7 * 2 = 14, pool is 12 ----
capacity 7 12 'log_level: debug'
commit_as c6 "Scale workers up for the import backlog"

capacity 7 12 'log_level: info'
commit_as c7 "Quieten the logs again"

capacity 6 10 'log_level: info'
commit_as c8 "Trim the pool back down and drop a worker"

capacity 8 14 'log_level: info'
write_file worker.py \
  '"""The job runner."""' \
  '' \
  '' \
  'def run(job):' \
  '    """Run one job to completion, reporting how long it took."""' \
  '    result = job()' \
  '    return result'
commit_as c9 "Scale up again for the weekend batch"
