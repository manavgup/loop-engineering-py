# Self-documenting Makefile. Run `make` (or `make help`) to list targets.
.DEFAULT_GOAL := help
PY ?= python3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with dev extras + pre-commit hooks
	$(PY) -m pip install -e '.[dev]'
	pre-commit install

lint: ## Run ruff + all pre-commit hooks
	ruff check backlog_grinder tests
	pre-commit run --all-files

format: ## Auto-format and auto-fix with ruff
	ruff format backlog_grinder tests
	ruff check --fix backlog_grinder tests

test: ## Run the unit suite + doctests
	$(PY) -m pytest -q
	$(PY) -m pytest --doctest-modules backlog_grinder -q

doctest: ## Run docstring doctests only
	$(PY) -m pytest --doctest-modules backlog_grinder -q

coverage: ## Run tests with coverage (fails under 85%)
	$(PY) -m pytest --cov=backlog_grinder --cov-report=term-missing --cov-fail-under=85 -q

grind: ## Grind a target repo: make grind CONFIG=grinder.json REPO=.
	$(PY) -m backlog_grinder.cli --config $(CONFIG) --repo $(REPO)

clean: ## Remove caches and coverage artifacts
	rm -rf .pytest_cache .ruff_cache htmlcov coverage.xml .coverage .backlog-grinder
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: help install lint format test doctest coverage grind clean
