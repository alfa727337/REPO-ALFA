PYTHON ?= python

.PHONY: install dev test lint format check browser docker-build

install:
	$(PYTHON) -m pip install -e .

browser:
	playwright install chromium

dev:
	$(PYTHON) -m pip install -e '.[dev]'

lint:
	ruff check repo_alfa tests

format:
	ruff format repo_alfa tests

check: lint test

test:
	pytest -q

docker-build:
	docker build -t repo-alfa .
