#!/usr/bin/env bash
# A rate-limit guard added in c2 and quietly dropped in c5 during a refactor
# that was about something else. Three commits of unrelated work on top, so the
# removal is nowhere near the tip and `git log -p` is eight diffs to read.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# turnstile' \
  '' \
  'Request middleware for the public API.'

write_file middleware.py \
  '"""Request middleware, applied in order."""' \
  '' \
  '' \
  'def handle(request):' \
  '    """Run the middleware chain and return a response."""' \
  '    authenticate(request)' \
  '    return respond(request)'

commit_as c1 "Add the middleware chain"

write_file middleware.py \
  '"""Request middleware, applied in order."""' \
  '' \
  '' \
  'def handle(request):' \
  '    """Run the middleware chain and return a response."""' \
  '    authenticate(request)' \
  '    enforce_rate_limit(request)' \
  '    return respond(request)'

commit_as c2 "Enforce the rate limit on every request"

write_file logging.py \
  '"""Structured request logging."""' \
  '' \
  '' \
  'def log(request, status):' \
  '    """One line per request."""' \
  '    return {"path": request["path"], "status": status}'

commit_as c3 "Add structured request logging"

write_file middleware.py \
  '"""Request middleware, applied in order."""' \
  '' \
  '' \
  'def handle(request):' \
  '    """Run the middleware chain and return a response."""' \
  '    authenticate(request)' \
  '    enforce_rate_limit(request)' \
  '    response = respond(request)' \
  '    response["headers"]["x-request-id"] = request["id"]' \
  '    return response'

commit_as c4 "Echo the request id on every response"

# --- c5: the refactor that dropped the guard ------------------------------
# The commit is about extracting the chain into a list. The rate limit is not
# in that list, and the diff looks like a tidy-up.
write_file middleware.py \
  '"""Request middleware, applied in order."""' \
  '' \
  '' \
  'CHAIN = ["authenticate"]' \
  '' \
  '' \
  'def handle(request):' \
  '    """Run the middleware chain and return a response."""' \
  '    for step in CHAIN:' \
  '        STEPS[step](request)' \
  '    response = respond(request)' \
  '    response["headers"]["x-request-id"] = request["id"]' \
  '    return response'

commit_as c5 "Make the middleware chain a list"

write_file logging.py \
  '"""Structured request logging."""' \
  '' \
  '' \
  'def log(request, status, duration_ms):' \
  '    """One line per request, with how long it took."""' \
  '    return {' \
  '        "path": request["path"],' \
  '        "status": status,' \
  '        "duration_ms": duration_ms,' \
  '    }'

commit_as c6 "Log how long each request took"

write_file README.md \
  '# turnstile' \
  '' \
  'Request middleware for the public API.' \
  '' \
  'The chain is declared in middleware.py as CHAIN.'

commit_as c7 "Document where the chain is declared"

write_file middleware.py \
  '"""Request middleware, applied in order."""' \
  '' \
  '' \
  'CHAIN = ["authenticate", "require_json"]' \
  '' \
  '' \
  'def handle(request):' \
  '    """Run the middleware chain and return a response."""' \
  '    for step in CHAIN:' \
  '        STEPS[step](request)' \
  '    response = respond(request)' \
  '    response["headers"]["x-request-id"] = request["id"]' \
  '    return response'

commit_as c8 "Require a JSON body on write requests"
