#!/usr/bin/env bash
set -Eeuo pipefail
release=/opt/yance/releases/website-web-20261020-01
candidate="$release/website"
override=/etc/systemd/system/yance-website.service.d/90-website-web-20261020-01.conf
switched=0
rollback() {
  code=$?
  if [ "$switched" = 1 ]; then
    echo 'ACTIVATION_FAILED_RESTORING_PREVIOUS_WEBSITE'
    sudo rm -f "$override"
    sudo systemctl daemon-reload
    sudo systemctl restart yance-website
    curl --retry 10 --retry-connrefused --retry-delay 1 --max-time 10 -fsS -o /dev/null http://127.0.0.1:3000/
  fi
  exit "$code"
}
trap rollback ERR
printf '%s  %s\n' e3c7b078d7d35f18cb44448951ca21ef1cf886c78aff9c2758c64093873379a0 /tmp/yance-website-web-20261020-01.tar.gz | sha256sum -c -
test ! -e "$override"
systemctl is-active --quiet yance-website
curl --max-time 15 -fsS http://127.0.0.1:3001/release.json | python3 -c 'import json,sys; assert json.load(sys.stdin)["release"]=="web-20261020-01"'
curl --max-time 15 -fsS -o /dev/null http://127.0.0.1:3001/api/v1/products
# Keep previous content-addressed assets available to already-open browser tabs.
cp -an /opt/yance/website/.next/static/. "$candidate/.next/static/"
sudo install -m 600 /etc/systemd/system/yance-website.service "$release/service-before.conf"
cat > "$release/website-override.conf" <<EOF
[Service]
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
WorkingDirectory=$candidate
ExecStart=
ExecStart=/usr/bin/node $candidate/node_modules/next/dist/bin/next start -p 3000 -H 127.0.0.1
EOF
sudo install -d -m 755 /etc/systemd/system/yance-website.service.d
switched=1
sudo install -m 644 "$release/website-override.conf" "$override"
sudo systemctl daemon-reload
sudo systemctl restart yance-website
curl --retry 15 --retry-connrefused --retry-delay 1 --max-time 10 -fsS http://127.0.0.1:3000/release.json | python3 -c 'import json,sys; assert json.load(sys.stdin)["release"]=="web-20261020-01"'
for route in / /pricing /login /security /policy-knowledge-base /api/v1/auth/config /api/v1/products; do
  curl --max-time 20 -fsS -o /dev/null -w "ACTIVE $route %{http_code}\n" "http://127.0.0.1:3000$route"
done
systemctl is-active --quiet yance-website
systemctl show yance-website -p WorkingDirectory -p MainPID
printf 'ACTIVATED '
date -u +%FT%TZ
