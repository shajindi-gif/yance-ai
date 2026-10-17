#!/usr/bin/env bash
# yance.ai uptime watchdog (S4 fix): 5-min probe of site + API with email alert.
#
# Installed as cron: */5 * * * * /opt/yance/yance-ai/ops/uptime_watchdog.sh >> /var/log/yance-watchdog.log 2>&1
# - Checks https://www.yance.ai/ and https://api.yance.ai/health
# - On failure: sends alert email via the SMTP creds in .env.prod (163), then a
#   30-minute cooldown file prevents alert storms; a recovery email is sent once
#   after the service comes back.
# - Exit 0 always (cron noise control); human reads the log.
set -u

ENV_FILE="/opt/yance/yance-ai/.env.prod"
STATE_DIR="/var/tmp/yance-watchdog"
COOLDOWN_SECONDS=1800
mkdir -p "$STATE_DIR"

SITE_URL="${WATCHDOG_SITE_URL:-https://www.yance.ai/}"
API_URL="${WATCHDOG_API_URL:-https://api.yance.ai/health}"

ts() { date '+%F %T'; }

smtp_send() {
  # $1 subject, $2 body — reads SMTP_* from .env.prod, never echoes secrets
  set -a; . "$ENV_FILE" >/dev/null 2>&1; set +a
  python3 - "$1" "$2" << 'PY'
import os, smtplib, sys
from email.message import EmailMessage
user, pw, host, port = os.environ.get("SMTP_USER",""), os.environ.get("SMTP_PASSWORD",""), os.environ.get("SMTP_HOST","smtp.163.com"), int(os.environ.get("SMTP_PORT","465"))
if not user or not pw:
    print("no SMTP creds; alert not emailed"); sys.exit(1)
msg = EmailMessage()
msg["From"] = user; msg["To"] = user; msg["Subject"] = f"[yance.ai 监控] {sys.argv[1]}"
msg.set_content(sys.argv[2])
try:
    with smtplib.SMTP_SSL(host, port, timeout=20) as s:
        s.login(user, pw); s.send_message(msg)
    print("alert email sent")
except Exception as e:
    print(f"alert email failed: {e}")
PY
}

probe() { # url -> http code or 000
  curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$1" 2>/dev/null || echo 000
}

FAILURES=""
SITE_CODE=$(probe "$SITE_URL")
API_CODE=$(probe "$API_URL")
[ "$SITE_CODE" = "200" ] || FAILURES="${FAILURES}site=${SITE_CODE}(${SITE_URL}) "
[ "$API_CODE" = "200" ] || FAILURES="${FAILURES}api=${API_CODE}(${API_URL}) "

DOWN_FILE="$STATE_DIR/down"
if [ -n "$FAILURES" ]; then
  NOW=$(date +%s)
  if [ -f "$DOWN_FILE" ]; then
    LAST=$(cat "$DOWN_FILE")
    if [ $((NOW - LAST)) -lt $COOLDOWN_SECONDS ]; then
      echo "$(ts) DOWN (in cooldown) $FAILURES"
      exit 0
    fi
  fi
  echo "$NOW" > "$DOWN_FILE"
  echo "$(ts) DOWN $FAILURES -> alerting"
  smtp_send "故障告警" "yance.ai 探测失败：$FAILURES
时间：$(ts)
主机：$(hostname)"
elif [ -f "$DOWN_FILE" ]; then
  rm -f "$DOWN_FILE" 2>/dev/null || true
  echo "$(ts) RECOVERED -> sending recovery notice"
  smtp_send "已恢复" "yance.ai 探测恢复正常（site=200 api=200）
时间：$(ts)"
else
  echo "$(ts) OK site=$SITE_CODE api=$API_CODE"
fi
exit 0
