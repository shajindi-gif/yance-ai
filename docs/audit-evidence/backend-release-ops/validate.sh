#!/usr/bin/env bash
set -Eeuo pipefail
release=/opt/yance/releases/backend-7f466d0
cat > "$release/Dockerfile.validation" <<'EOF'
FROM yance-backend:7f466d0
USER root
COPY constraints-release.txt /tmp/constraints-release.txt
RUN pip install -c /tmp/constraints-release.txt 'pytest>=9.0.3,<10' 'pytest-cov>=6,<7' 'ruff>=0.9,<1' pip-audit
USER yance
EOF
docker build -f "$release/Dockerfile.validation" -t yance-backend-validation:7f466d0 "$release/yance-ai" > "$release/validation-image.log" 2>&1
docker network create --internal yance-validation-7f466d0 > /dev/null
docker run -d --name yance-validation-db-7f466d0 --network yance-validation-7f466d0 --memory 384m -e POSTGRES_USER=yance -e POSTGRES_DB=yance_release_test -e POSTGRES_HOST_AUTH_METHOD=trust pgvector/pgvector:pg16 > /dev/null
for attempt in {1..60}; do
  if docker exec yance-validation-db-7f466d0 pg_isready -U yance -d yance_release_test > /dev/null 2>&1; then break; fi
  sleep .5
done
docker run --name yance-validation-7f466d0 --network yance-validation-7f466d0 --memory 1200m --memory-swap 1800m --cpus 1.5 \
 -e PYTHONPATH=/app -e APP_ENV=test -e DATABASE_URL=postgresql+psycopg://yance@yance-validation-db-7f466d0:5432/yance_release_test -e YANCE_TEST_DATABASE_ACK=yance_release_test \
 -e JWT_SECRET=synthetic-release-test-secret-32-chars -e BOOTSTRAP_TOKEN=synthetic-release-bootstrap-token -e TENANT_PROVISIONING_TOKEN=synthetic-release-provision-token -e API_KEY_PEPPER=synthetic-release-api-pepper-32-chars \
 -e EMAIL_ENABLED=false -e LLM_DEFAULT_PROVIDER=mock -e DEMO_FEATURES_ENABLED=false \
 -v "$release/yance-ai/pyproject.toml:/app/pyproject.toml:ro" -v "$release/yance-ai/tests:/app/tests:ro" -v "$release/yance-ai/docs:/app/docs:ro" \
 yance-backend-validation:7f466d0 sh -ec 'ruff check app tests alembic scripts/verify_database_snapshot.py; python -m compileall -q app; python scripts/export_openapi.py --check; alembic upgrade head; alembic check; python -m pytest --cov=app --cov-report=term --cov-fail-under=50 --tb=short; python evals/run_evals.py run --no-persist; pip check' > "$release/pg16-validation.log" 2>&1
printf 'PG16_VALIDATION_COMPLETE\n'
tail -8 "$release/pg16-validation.log"
