# Fallback env loader for shells without direnv.
#   source scripts/env.sh
# Adds the Athena CLI wrappers to PATH and exports brand credentials.
ATHENA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export ATHENA_DIR
export PATH="$ATHENA_DIR/bin:$PATH"
if [ -f "$ATHENA_DIR/.env" ]; then
  set -a
  . "$ATHENA_DIR/.env"
  set +a
fi
