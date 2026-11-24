#!/bin/bash
set -Eeuo pipefail
b=/opt/yance/backups/frontend-20261110-01
rm -f /etc/systemd/system/yance-website.service.d/zzzzzzz-frontend-20261110.conf
ln -sfn "$(cat "$b/website-path.txt")" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
printf 'OLD_WEBSITE_RESTORED\n'
