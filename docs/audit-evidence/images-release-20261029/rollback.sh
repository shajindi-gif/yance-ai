#!/usr/bin/env bash
set -euo pipefail
old=/opt/yance/releases/growth-20261029-01/website
test -f "$old/.next/BUILD_ID"
rm -f /etc/systemd/system/yance-website.service.d/99-images-20261029-01.conf
ln -sfn "$old" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
echo PREVIOUS_WEBSITE_RESTORED_BACKEND_UNTOUCHED
