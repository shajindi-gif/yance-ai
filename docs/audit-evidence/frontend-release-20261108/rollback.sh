#!/bin/bash
set -Eeuo pipefail
b=/opt/yance/backups/frontend-20261108-02
rm -f /etc/systemd/system/yance-website.service.d/zzzzz-frontend-20261108.conf
ln -sfn "$(cat "$b/website-path.txt")" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
printf 'OLD_WEBSITE_RESTORED\n'
