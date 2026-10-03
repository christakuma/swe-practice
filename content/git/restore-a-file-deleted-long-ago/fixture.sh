#!/usr/bin/env bash
# A deploy healthcheck deleted three commits ago in a tidy-up, and wanted back
# now. The deletion is committed and published, so the fix is a new commit.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# shipyard' \
  '' \
  'Container deploys. tools/ holds the scripts CI calls.'

write_file tools/healthcheck.sh \
  '#!/usr/bin/env bash' \
  '# Fails the deploy if the new container does not answer in five seconds.' \
  'set -euo pipefail' \
  'curl --fail --max-time 5 http://localhost:8080/healthz' \
  'echo "healthy"'

commit_as c1 "Add deploy healthcheck"

write_file deploy.sh \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  'echo "deploying"' \
  'bash tools/healthcheck.sh'

commit_as c2 "Add the deploy script"

# --- c3: the tidy-up that went one file too far --------------------------
rm tools/healthcheck.sh
write_file deploy.sh \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  'echo "deploying"'

commit_as c3 "Remove unused scripts from tools"

write_file README.md \
  '# shipyard' \
  '' \
  'Container deploys. tools/ holds the scripts CI calls.' \
  '' \
  'Deploys are triggered from the release pipeline.'

commit_as c4 "Describe how deploys are triggered"

write_file rollback.sh \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  'echo "rolling back to the previous image"'

commit_as c5 "Add a rollback script"
