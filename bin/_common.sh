# Shared helpers for the Athena CLI wrappers.
#
# Model: we do NOT fork Cyclone's CLI code. Each wrapper builds the requested
# tool from the Cyclone source tree on demand (only when the source is newer
# than the last build), loads Athena's own credentials, isolates per-brand
# state, then execs the binary. Result: one source of truth (the Cyclone
# clone), always-current binaries, Athena-scoped credentials.

set -euo pipefail

# Athena repo root (this file lives in <root>/bin).
ATHENA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Cyclone source tree. Overridable via CYCLONE_DIR (env or .env).
CYCLONE_DIR="${CYCLONE_DIR:-/Users/conrad/workspace/cyclone/cyclone}"

BUILD_DIR="$ATHENA_DIR/bin/.build"
# Isolated HOME so os.UserConfigDir() (which the Shopify CLI uses to persist its
# OAuth token) resolves to an Athena-only path. On macOS this is
# $HOME/Library/Application Support, and Go IGNORES XDG_CONFIG_HOME there — so
# overriding HOME is the only reliable per-brand isolation lever.
HOME_DIR="$ATHENA_DIR/.home"

die() { echo "athena-cli: $*" >&2; exit 1; }

load_env() {
  local envfile="$ATHENA_DIR/.env"
  if [ -f "$envfile" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$envfile"
    set +a
  else
    echo "athena-cli: warning: $envfile not found — copy .env.example to .env and fill it in (see docs/CREDENTIALS.md)" >&2
  fi
  # Anchor a relative service-account key path at the repo root so it resolves
  # regardless of the caller's working directory.
  if [ -n "${GMAIL_SA_KEY:-}" ] && [ "${GMAIL_SA_KEY#/}" = "$GMAIL_SA_KEY" ]; then
    export GMAIL_SA_KEY="$ATHENA_DIR/${GMAIL_SA_KEY#./}"
  fi
}

# build_go <tool-subdir> <binary-name>  -> prints the built binary path.
# Rebuilds only when a .go file under the source is newer than the binary.
build_go() {
  local subdir="$1" name="$2"
  local src="$CYCLONE_DIR/tools/$subdir"
  [ -d "$src" ] || die "Cyclone source not found at $src (set CYCLONE_DIR in .env)"
  command -v go >/dev/null 2>&1 || die "go toolchain not found on PATH"
  mkdir -p "$BUILD_DIR"
  local bin="$BUILD_DIR/$name"
  if [ ! -x "$bin" ] || [ -n "$(find "$src" -name '*.go' -newer "$bin" -print -quit 2>/dev/null)" ]; then
    ( cd "$src" && go build -o "$bin" . ) || die "build failed for $name"
  fi
  printf '%s\n' "$bin"
}

# run_go <tool-subdir> <binary-name> [args...]
run_go() {
  local subdir="$1" name="$2"
  shift 2
  load_env
  # Best-effort throttled pull so upstream CLI updates flow in. Never fatal
  # (offline is fine — we just build from whatever source is on disk).
  if [ "${ATHENA_AUTO_PULL:-1}" != "0" ]; then
    "$ATHENA_DIR/bin/refresh" >/dev/null 2>&1 || true
  fi
  local bin
  bin="$(build_go "$subdir" "$name")"
  mkdir -p "$HOME_DIR"
  # HOME override isolates the Shopify OAuth token cache to Athena. Build ran
  # above with the real HOME so the Go build cache is untouched.
  exec env HOME="$HOME_DIR" "$bin" "$@"
}
