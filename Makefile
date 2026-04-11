PYTHON ?= python3
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate

.PHONY: venv install-dev format lint test run-cli run-daemon clean

venv:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip

install-dev: venv
	$(ACTIVATE) && pip install -e ".[dev]"

format:
	$(VENV)/bin/ruff format src tests

lint:
	$(VENV)/bin/ruff check src tests

test:
	$(VENV)/bin/pytest

run-cli:
	$(VENV)/bin/kbd-auto-layoutctl --help

run-daemon:
	$(VENV)/bin/kbd-auto-layoutd

clean:
	rm -rf $(VENV) build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
