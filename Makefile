.PHONY: help install-api dev-redis dev-api dev-worker dev-web dev test-api smoke clean

help:
	@echo "Targets disponibles:"
	@echo "  install-api  - Instala deps backend (requirements-api.txt)"
	@echo "  dev-redis    - Levanta Redis en Docker (puerto 6379)"
	@echo "  dev-api      - uvicorn FastAPI con reload en :8000"
	@echo "  dev-worker   - Worker RQ que procesa la cola"
	@echo "  dev-web      - Next.js dev server en :3000"
	@echo "  dev          - dev-api + dev-worker en paralelo (requires GNU make)"
	@echo "  smoke        - Smoke test E2E del backend (ver scripts/smoke_api.sh)"
	@echo "  clean        - Limpia tmp/ y __pycache__"

install-api:
	pip install -r requirements-api.txt

dev-redis:
	docker run --rm -d --name unibabot-redis -p 6379:6379 redis:7-alpine || echo "Redis ya corriendo o usar 'make dev-redis-stop'"

dev-redis-stop:
	docker stop unibabot-redis

dev-api:
	uvicorn src.api.main:app --reload --port 8000

dev-worker:
	python -m src.api.jobs.worker

dev-web:
	cd web && pnpm dev

dev:
	$(MAKE) -j2 dev-api dev-worker

test-api:
	pytest tests/api/ -v

smoke:
	bash scripts/smoke_api.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f tmp/uploads/*.pdf 2>/dev/null || true
