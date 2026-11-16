set -euo pipefail
r=/opt/yance/releases/commercial-20261108-01
b=/opt/yance/backups/commercial-20261108-01
curl --max-time 15 -fsS https://yance.ai/release.json
printf '\n'
curl --max-time 15 -fsS https://yance.ai/api/runtime-version
printf '\n'
[ "$(curl --max-time 15 -s -o /dev/null -w '%{http_code}' https://yance.ai/api/v1/policies/evidence-search?q=test)" = 401 ]
python3 /home/ubuntu/yance-commercial-1108-verify-env.py
docker exec yance-prod-api-1 python -c 'import importlib.metadata as m; print({n:m.version(n) for n in ["pypdf","brotli","dnspython"]})'
docker exec yance-prod-agent-worker-1 sha256sum /app/app/services/agents/policy_scan.py
systemctl is-active yance-website yance-collector
docker exec -i yance-prod-db-1 sh -ec 'exec psql -X -v ON_ERROR_STOP=1 -P pager=off -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
SELECT version_num FROM alembic_version;
SELECT status,count(*) FROM orders WHERE resource_type='report' GROUP BY status;
SELECT status,count(*) FROM agent_runs GROUP BY status;
SELECT max(finished_at) AS last_collection_finish FROM policy_collection_runs;
COMMIT;
SQL
test -s "$b/database.dump"
cmp "$b/live-counts.txt" "$b/restored-counts.txt"
df -h /
echo LIVE_RUNTIME_CONFIG_SCHEMA_AUTH_COLLECTION_VERIFIED
