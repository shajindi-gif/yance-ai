#!/usr/bin/env bash
# yance-collector-guard — 15-minute health/guard pass for the host-native collector.
#
# What it does (and only this):
#   1. enforces the free-disk floor by writing the collector's own PAUSED flag;
#   2. lifts *its own* disk pause once space recovers (never touches an operator pause);
#   3. reports heartbeat staleness and a down-but-enabled service;
#   4. appends one line per run to /var/log/yance/guard.log (rotated daily).
#
# It never starts, stops or restarts the collector, never touches the database,
# and never downloads anything.

set -Euo pipefail

ENV_FILE="/etc/yance/collector.env"
RAW_DIR="/var/lib/yance/policy_raw"
LOG="/var/log/yance/guard.log"
SERVICE="yance-collector"
GUARD_TAG="guard:"

mkdir -p "$(dirname "$LOG")"

read_setting() {
  # $1 = settings field name (upper snake), $2 = default
  local key="$1" def="${2:-}"
  local val=""
  if [[ -r "$ENV_FILE" ]]; then
    val="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"')"
  fi
  printf '%s' "${val:-$def}"
}

FLOOR_MB="$(read_setting POLICY_COLLECTION_MIN_FREE_DISK_MB 3000)"
CYCLE_S="$(read_setting POLICY_COLLECTION_SCHEDULER_CYCLE_SECONDS 600)"
[[ "$FLOOR_MB" =~ ^[0-9]+$ ]] || FLOOR_MB=3000
[[ "$CYCLE_S" =~ ^[0-9]+$ ]] || CYCLE_S=600
RECOVER_MB=$(( FLOOR_MB + 500 ))
STALE_AFTER=$(( CYCLE_S * 3 + 900 ))

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
emit() { printf '%s %s\n' "$(ts)" "$*" >>"$LOG"; }

free_mb="$(df -Pm "$RAW_DIR" 2>/dev/null | awk 'NR==2 {print $4}')"
[[ "$free_mb" =~ ^[0-9]+$ ]] || free_mb=-1

PAUSE_FLAG="$RAW_DIR/PAUSED"
paused_by_guard=0
if [[ -f "$PAUSE_FLAG" ]] && head -c 64 "$PAUSE_FLAG" 2>/dev/null | grep -q "^${GUARD_TAG}"; then
  paused_by_guard=1
fi

action="none"
if [[ "$free_mb" -ge 0 && "$free_mb" -lt "$FLOOR_MB" && "$paused_by_guard" -eq 0 ]]; then
  # Fail closed: stop downloading before the disk is full. The worker reads this
  # flag at the next cycle boundary — no restart needed, no restart performed.
  printf '%slow_disk free=%sMB floor=%sMB at=%s\n' "$GUARD_TAG" "$free_mb" "$FLOOR_MB" "$(ts)" >"$PAUSE_FLAG"
  chown yancecoll:yancecoll "$PAUSE_FLAG" 2>/dev/null || true
  chmod 0640 "$PAUSE_FLAG" 2>/dev/null || true
  action="paused_low_disk"
elif [[ "$free_mb" -ge "$RECOVER_MB" && "$paused_by_guard" -eq 1 ]]; then
  rm -f "$PAUSE_FLAG"
  action="resumed_disk_recovered"
fi

# Heartbeat (written atomically by the worker each cycle).
hb_status="absent"
hb_age=""
HBEAT="$RAW_DIR/collector_state.json"
if [[ -f "$HBEAT" ]]; then
  hb_status="present"
  hb_age="$(python3 - "$HBEAT" <<'PY' 2>/dev/null || echo ""
import json, sys
from datetime import datetime, UTC
def parse(value):
    # The worker writes datetime.isoformat() (microseconds, +00:00); older builds
    # wrote "%Y-%m-%dT%H:%M:%S". Accept both instead of silently reporting no age.
    text = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    last = data.get("last_cycle_at")
    print("" if not last else int((datetime.now(UTC) - parse(last)).total_seconds()))
except Exception:
    print("")
PY
)"
fi

svc_active="$(systemctl is-active "$SERVICE" 2>/dev/null || echo unknown)"
svc_enabled="$(systemctl is-enabled "$SERVICE" 2>/dev/null || echo unknown)"

level="ok"
notes=""
if [[ "$svc_enabled" == "enabled" && "$svc_active" != "active" ]]; then
  level="warn"; notes="${notes} service_not_running"
fi
if [[ "$hb_age" =~ ^[0-9]+$ && "$hb_age" -gt "$STALE_AFTER" ]]; then
  level="warn"; notes="${notes} heartbeat_stale_${hb_age}s"
fi
if [[ "$free_mb" -ge 0 && "$free_mb" -lt "$FLOOR_MB" ]]; then
  level="warn"; notes="${notes} disk_below_floor"
fi

emit "level=${level} action=${action} free_mb=${free_mb} floor_mb=${FLOOR_MB} heartbeat=${hb_status} age_s=${hb_age:-na} svc=${svc_active}/${svc_enabled}${notes:+ notes:${notes}}"

# Keep guard.log from ever growing unbounded even if logrotate is disabled.
if [[ -f "$LOG" ]]; then
  size_kb="$(du -k "$LOG" | awk '{print $1}')"
  if [[ "$size_kb" -gt 20480 ]]; then
    tail -n 5000 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  fi
fi

exit 0
