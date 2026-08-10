#!/usr/bin/env bash
# push_gmail_drafts.sh — stage round-2 outreach emails as Gmail drafts.
#
# Reads outreach/drafts/round2-send-manifest.csv and calls
#   gmail-admin drafts create --to <email> --subject <subj> --body-file <path>
# for every row. `drafts create` is a RAW primitive: it does NOT send, and does
# NOT modify touchpoints.csv / stage / labels. Drafts are reversible (delete in
# Gmail or via `gmail-admin drafts delete <id>`). Nothing in this script sends mail.
#
# Env:
#   GMAIL_SA_KEY       (required) service-account key path
#   GMAIL_IMPERSONATE  (default conrad@athenauraguard.com)
#   DRY_RUN=1          preview MIME only, create no drafts
#   SLEEP_SECS=N       pause between calls (default 1)
#
# Output: outreach/drafts/round2-gmail-draftlog.csv  (id,email,subject,draft_id,status,attempts)
set -uo pipefail

ROOT="/Users/conrad/conductor/workspaces/athena/port-au-prince"
cd "$ROOT" || exit 1

: "${GMAIL_SA_KEY:?set GMAIL_SA_KEY to the service-account key path}"
export GMAIL_SA_KEY
export GMAIL_IMPERSONATE="${GMAIL_IMPERSONATE:-conrad@athenauraguard.com}"

GMAIL="bin/gmail-admin"
MANIFEST="${MANIFEST:-outreach/drafts/round2-send-manifest.csv}"
LOG="${LOG:-outreach/drafts/round2-gmail-draftlog.csv}"
DRY="${DRY_RUN:-0}"
SLEEP="${SLEEP_SECS:-1}"

[ -x "$GMAIL" ]     || { echo "gmail-admin wrapper not found at $GMAIL" >&2; exit 1; }
[ -f "$MANIFEST" ]  || { echo "manifest not found at $MANIFEST" >&2; exit 1; }

# Preflight auth (read-only).
echo "preflight: gmail-admin auth check ..."
if ! "$GMAIL" auth check >/dev/null 2>&1; then
  echo "ABORT: auth check failed — check GMAIL_SA_KEY / GMAIL_IMPERSONATE" >&2
  exit 1
fi
echo "  auth ok as $GMAIL_IMPERSONATE  (DRY_RUN=$DRY)"

# Robust CSV -> TSV (id \t email \t subject \t body_path); handles quoted subjects.
TSV="$(mktemp)"
trap 'rm -f "$TSV"' EXIT
python3 - "$MANIFEST" > "$TSV" <<'PY'
import csv, sys
rows = list(csv.reader(open(sys.argv[1])))
for r in rows[1:]:
    if len(r) < 5:
        continue
    sys.stdout.write("\t".join([r[0], r[1], r[2], r[4]]) + "\n")
PY

echo "id,email,subject,draft_id,status,attempts" > "$LOG"

do_create() {  # to subject bodyfile -> prints tool output, returns tool rc
  local to="$1" subj="$2" body="$3"
  local -a args=(drafts create --to "$to" --subject "$subj" --body-file "$body")
  [ "$DRY" = "1" ] && args+=(--dry-run)
  "$GMAIL" "${args[@]}" 2>&1
}

total=0 ok=0 fail=0
while IFS=$'\t' read -r id email subject body; do
  [ -z "${id:-}" ] && continue
  total=$((total+1))

  if [ ! -f "$body" ]; then
    echo "$id,$email,\"$subject\",,MISSING_BODY,0" >> "$LOG"
    echo "  [$total] $id — MISSING body $body" >&2
    fail=$((fail+1)); continue
  fi

  attempt=1; draft_id=""; status="error"; out=""
  while [ "$attempt" -le 2 ]; do
    out="$(do_create "$email" "$subject" "$body")"; rc=$?
    draft_id="$(printf '%s\n' "$out" | grep -oE 'id=[^ ]+' | head -1 | cut -d= -f2)"
    if [ "$rc" -eq 0 ] && { [ -n "$draft_id" ] || [ "$DRY" = "1" ]; }; then
      status="created"; [ "$DRY" = "1" ] && status="dryrun"
      break
    fi
    status="error"; draft_id=""
    [ "$attempt" -eq 1 ] && sleep 2
    attempt=$((attempt+1))
  done
  used=$attempt; [ "$used" -gt 2 ] && used=2

  echo "$id,$email,\"$subject\",${draft_id},${status},${used}" >> "$LOG"
  if [ "$status" = "created" ] || [ "$status" = "dryrun" ]; then
    ok=$((ok+1)); echo "  [$total] $id — $status ${draft_id}"
  else
    fail=$((fail+1)); echo "  [$total] $id — FAILED after ${used} tries: $(printf '%s' "$out" | tail -1)" >&2
  fi
  sleep "$SLEEP"
done < "$TSV"

echo
echo "done: $total processed, $ok ok, $fail failed"
echo "log: $LOG"
[ "$fail" -eq 0 ]
