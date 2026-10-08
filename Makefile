# Relay — one command per task. `make help` lists them.
.DEFAULT_GOAL := help
BACKEND := cd backend &&
FRONTEND := cd frontend &&

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install backend (uv) and frontend (npm) dependencies
	$(BACKEND) uv sync
	$(FRONTEND) npm install

up: ## Start Postgres, Redis, LocalStack (SQS + S3) and Mailpit
	docker compose up -d --wait postgres redis localstack mailpit

up-full: ## Same, plus the API and worker as containers (API on :8020)
	docker compose --profile full up -d --build

down: ## Stop everything
	docker compose --profile full down

migrate: ## Apply database migrations
	$(BACKEND) uv run alembic upgrade head

seed: ## Demo data: 2 organisations, 5,000 tickets
	$(BACKEND) uv run python -m app.seed

seed-large: ## Demo data + 1,000,000 tickets for the performance check
	$(BACKEND) uv run python -m app.seed --large

api: ## Run the API with reload on :8030
	$(BACKEND) uv run uvicorn app.main:app --reload --port 8030

worker: ## Run the worker (with the local scheduler for SLA scans)
	$(BACKEND) uv run python -m app.worker --schedule

web: ## Run the React app on :5190 (proxies /api to :8030)
	$(FRONTEND) npm run dev

gen-client: ## Regenerate TypeScript types and enums from the API's OpenAPI
	$(BACKEND) uv run python -m app.openapi > ../frontend/packages/api-client/openapi.json
	$(FRONTEND) npm run gen-client

test: ## Backend (unit + integration) and frontend tests
	$(BACKEND) uv run pytest --cov=app
	$(FRONTEND) npm test

e2e: ## Playwright journey (needs up + api + worker)
	$(FRONTEND) npm run e2e

lint: ## ruff, mypy, ESLint, Stylelint, tsc
	$(BACKEND) uv run ruff check . && uv run ruff format --check . && uv run mypy app
	$(FRONTEND) npm run lint && npm run typecheck

load: ## k6 load test against the local API (see loadtest/README.md)
	k6 run loadtest/tickets.js

cdk-synth: ## Synthesize the AWS CloudFormation templates (no deploy)
	cd infra/cdk && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 npx --yes aws-cdk@2 synth --quiet

cdk-test: ## CDK assertion tests
	cd infra/cdk && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 uv run pytest -q

diagrams: ## Regenerate draw.io diagrams and PNGs
	python3 docs/architecture/gen_diagrams.py --png

.PHONY: help install up up-full down migrate seed seed-large api worker web gen-client test e2e lint load cdk-synth cdk-test diagrams
