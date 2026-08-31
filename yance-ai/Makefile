.PHONY: dev-up dev-down logs test lint migrate smoke prod-up prod-down

dev-up:
	cp .env.example .env 2>/dev/null || true
	docker compose -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.dev.yml down

prod-up:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=200

migrate:
	docker compose -f docker-compose.prod.yml run --rm migrate

test:
	pytest

lint:
	ruff check .

smoke:
	sh scripts/smoke_test.sh http://localhost

