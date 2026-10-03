#!/usr/bin/env bash
# A deploy script committed together with the .env file holding the live API
# token. Unpushed -- origin/main is one commit behind -- so the commit that
# contains the secret can still be replaced rather than merely undone.
source "$PRACTICE_FIXTURE_LIB"

git init --quiet
git config core.fileMode false
git config core.autocrlf false
git config core.eol lf

write_file README.md \
  '# publisher' \
  '' \
  'Pushes the built site to the CDN. Run ./deploy.sh.'

commit_as c1 "Add project skeleton"

mkremote origin
publish origin main

# --- c2: the deploy script, and the secret that came along with it --------
write_file deploy.sh \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  '# Reads API_TOKEN from the environment, which is loaded from .env.' \
  'source ./.env' \
  'rsync -a --delete ./build/ "$CDN_HOST:/srv/www/"'

write_file .env \
  '# Local secrets. NOT for version control.' \
  'API_TOKEN=sk-live-4f19c0aa8be24d77' \
  'CDN_HOST=deploy@cdn.internal'

commit_as c2 "Add deploy script"
